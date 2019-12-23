import curses
import curses.textpad
import time
import logging
from PyExpLabSys.drivers.fug import FUGNTN140Driver
from PyExpLabSys.common.sockets import DateDataPullSocket
#from pull import DateDataPullClient
from heat_ramp import PowerCalculatorClassOmicron
import fit_ramp
#import numpy as np

import threading

logging.basicConfig(filename='power_supply.log', level=logging.WARNING)
LOGGER = logging.getLogger(__name__)

MARKER = ' -> '
EMPTY = ' '*len(MARKER)
CODENAMES = [
    'voltage_mon',
    #'voltage_set',
    'current_mon',
    #'current_set',
    'temperature_set',
    'P_error',
    #'I_error',
    ]

class CursesTui(threading.Thread):
    """ Interface for the power supply for Omicron TPD's """
    
    def __init__(self, powersupplyclass, pullsocket):
        threading.Thread.__init__(self)
        self.psc = powersupplyclass
        self.calc = PowerCalculatorClassOmicron(ramp=1.0)
        self.pullsocket = pullsocket
        # Setting parameters
        self.settings = {}
        self.settings['halfdelay'] = 1
        # Value parameters
        self.values = {}
        self.values['status'] = 'Starting'
        self.values['voltage_mon'] = 0
        self.values['voltage_set'] = 0
        self.values['current_mon'] = 0
        self.values['current_set'] = 0
        #self.values['power_mon'] = 0
        #self.values['power_set'] = 0
        self.values['temperature_set'] = None
        self.values['P_error'] = 0
        #self.values['I_error'] = 0
        # Ramp parameters
        self.ramp = {}
        # - Instument specific functions: (not used right now)
        self.ramp['current'] = [0, 0] # [ramp restriction value, slow_start?]
        self.ramp['voltage'] = [0, 0]
        # - Ramp control inputs:
        self.ramp['value'] = 1 # Kelvin per second
        self.ramp['stop current'] = 6.0
        self.ramp['stop temperature'] = 50
        if self.calc:
            self.calc.pid.pid_p = 0.06    # PID proportional term
            self.calc.pid.pid_i = 0.00001 # PID integration term
            self.calc.pid.pid_d = 0.0     # PID differential term
            #self.calc.pid.p_min = -1.0
        self.ramp['start current'] = 0.0 # Adopt starting current as PID minimum current
        self.ramp['standby current'] = 1.0
        self.ramp['wait'] = 0.1
        self.ramp['track'] = 1
        # Initialize screens and draw boxes
        self.screen = curses.initscr()
        curses.textpad.rectangle(self.screen, 0,0, 8,79)
        curses.textpad.rectangle(self.screen, 9,0, 19,30)
        curses.textpad.rectangle(self.screen, 9,32, 27,79)
        self.win1 = curses.newwin(7,77, 1,1)
        self.win2 = curses.newwin(8,28, 10,1)
        self.win3 = curses.newwin(15,44, 10,33)
        self.screen.refresh()
        curses.cbreak()
        curses.noecho()
        curses.halfdelay(self.settings['halfdelay'])
        self.quit = False
        self.menu = {
            1: 'Set voltage',
            2: 'Set current',
            3: 'Run ramp',
            4: 'Reset',
            5: 'Ramp settings',
            6: 'Fitted ramp',
            0: 'Quit (Q)',
        }
        self.cursor = 0
        self.lst = [1, 2, 3, 4, 5, 6, 0]
        self.update_display()
        self.update_menu()

    def run_ramp(self, fit=False, limit_ramp=False):
        """Ramp function (PID controlled heating)"""
        
        self.values['status'] = 'Ramp running... (exit on "q")'
        self.update_display()
        if self.ramp['track']:
            time_start = time.time()
            self.win3.clrtobot()
            self.win3.refresh()

        # Prepare ramp limitation
        self.psc.ramp_current(self.ramp['current'][0], program=self.ramp['current'][1])
        if limit_ramp:
            tau = 0.25
            averaging_time = 30.
            avg_N = int(averaging_time/tau)
            #avg = np.ones(avg_N) * tau * self.ramp['current'][0]
            avg = [ tau * self.ramp['current'][0] ]
            avg = avg * avg_N
            avg_counter = 0
        else:
            new_ramp = self.ramp['current'][0]

        # Start PID calculator
        curses.halfdelay(1)
        #self.values['status'] = 'Ramp running..'
        self.calc.ramp = self.ramp['value']

        # Set the "zero" for the PID control
        self.update_display()
        self.calc.zero = self.values['current_mon']
        self.calc.initialize()
        time.sleep(0.1)

        # PID controlled heating ramp
        t0 = time.time()
        if fit is True:
            tset_start = self.calc.values['setpoint']
            local_calc = fit_ramp.FitParameters()
        while True:

            # Use PID setpoint
            if fit is False:
                #setpoint = self.calc.values['pid'] + self.ramp['start current']
                setpoint = self.calc.get_setpoint()

            # Use fitted setpoint
            else:
                t_now = time.time() - t0
                self.calc.get_temperature()
                self.calc.values['setpoint'] = tset_start + t_now*0.5 # hardcoded ramp
                #if t_now < fit_ramp.t_change:
                #    param = fit_ramp.param1
                #else:
                #    param = fit_ramp.param2
                #setpoint = fit_ramp.poly_current(t_now, param)
                #if t_now > fit_ramp.t_end: # Make loop break on next if
                #    setpoint = self.ramp['stop current'] + 1
                setpoint = local_calc.get_setpoint(t_now)
                if not setpoint:
                    setpoint = self.ramp['stop current'] + 1

            # Break if current would be set too high
            if (setpoint >= self.ramp['stop current']):
                self.values['status'] = 'Halt: Max current reached'
                self.update_display()
                break
            # Break if temperature gets too high
            elif (self.calc.values['temperature']  >= self.ramp['stop temperature']):
                self.values['status'] = 'Halt: Max temperature reached'
                self.update_display()
                break
            # Implement new setpoint
            #if setpoint > self.values['current_set']:
            self.psc.set_current(setpoint)
            self.values['current_set'] = setpoint
            self.values['temperature_set'] = self.calc.values['setpoint']

            # Pause system to allow current to change
            time.sleep(self.ramp['wait'])
            ########################## in this form to provide 'break' option
            c = self.screen.getch()  # (important with the 'halfdelay(1)' option)
            if c == ord('q'):        #
                break                #
            ##########################
            self.update_display()

            # Set new limitation on current ramp
            if limit_ramp:
                avg[avg_counter] = self.values['current_mon']
                avg_counter += 1
                if avg_counter == avg_N:
                    avg_counter = 0
                new_ramp = 0.9*abs(sum(avg))/averaging_time/avg_N
                self.psc.ramp_current(new_ramp, program=-1)

            # Write output to screen if enabled
            if self.ramp['track']:
                box = ''
                box += 'Temp set: {:.4} C\n'.format(self.calc.values['setpoint'])
                box += 'Temp now: {:.4} C\n'.format(self.calc.values['temperature'])
                box += 'PID error: {}\n'.format(self.calc.pid.error[1])
                box += 'Ramp value: {}\n'.format(new_ramp)
                box += 'Loop time: {}\n'.format(time.time()-time_start)
                time_start = time.time()
                for i in range(6):
                    box += ' '*30 + '\n'
                self.win3.addstr(0,0, box)
                self.win3.refresh()
        # Return normal settings
        self.calc.stop()
        self.values['temperature_set'] = self.calc.values['setpoint']
        self.psc.ramp_current(self.ramp['current'][0], program=2)
        self.psc.set_current(self.ramp['standby current'])
        self.values['current_set'] = self.ramp['standby current']
        self.values['status'] += ' - Ramp completed'
        self.update_display()
        curses.halfdelay(self.settings['halfdelay'])

    def stop(self):
        # Return terminal to before curses changes
        self.quit = True
        self.screen.keypad(0)
        curses.nocbreak()
        curses.echo()
        curses.endwin()
        # Stop linked threads
        self.psc.stop()
        print('Power supply stopped')
        self.calc.stop()
        print('PID calculator stopped')
        self.pullsocket.stop()
        print('Pullsocket stopped')

    def update_values(self):
        """Read current and voltage from power supply """
        self.values['voltage_mon'] = self.psc.monitor_voltage()
        self.values['current_mon'] = self.psc.monitor_current()
        #self.values['power_mon'] = self.values['voltage_mon']*self.values['current_mon']
        self.update_socket()

    def update_socket(self):
        """Write values to pullsocket """
        if self.calc:
            self.values['P_error'] = self.calc.pid.error[1]
            #self.values['I_error'] = self.calc.pid.int_error
        for codename in CODENAMES:
            self.pullsocket.set_point_now(codename, self.values[codename])

    def update_display(self):
        """Refreshes the window with values"""
        self.update_values()
        try:
            self.display = '' + \
                           'Status: {: <50s}\n'.format(self.values['status']) + \
                           '\n' + \
                           'Voltage setpoint:        Current setpoint:            \n' + \
                           ' {: <24f} {: <28f}\n'.format(self.values['voltage_set'], self.values['current_set']) + \
                           '\n' + \
                           'Voltage value:           Current value:               \n' + \
                           ' {: <24f} {: <28f}'.format(self.values['voltage_mon'], self.values['current_mon'])
        except ValueError:
            LOGGER.warning(repr(self.values['status']))
            LOGGER.warning(repr(self.values['voltage_set']))
            LOGGER.warning(repr(self.values['voltage_mon']))
            LOGGER.warning(repr(self.values['current_set']))
            LOGGER.warning(repr(self.values['current_mon']))
            self.display = 'ValueError...'
        self.win1.clrtobot()
        self.win1.addstr(0,0, self.display)
        self.win1.refresh()

    def update_menu(self):
        """Refreshes the options window"""
        self.menu_win = ''
        for i in range(len(self.lst)):
            if self.cursor == i:
                cursor = MARKER
            else:
                cursor = EMPTY
            self.menu_win = self.menu_win + cursor + '{}: {}\n'.format(self.lst[i], self.menu[self.lst[i]])
        self.win2.clrtobot()
        self.win2.addstr(0,0, 'Options: ')
        self.win2.addstr(0,0, self.menu_win)
        self.win2.refresh()

    def get_input(self, y=1, x=2, prompt='Enter value:'):
        """Receives an input value from user and returns a float. Susceptible to errors..."""
        curses.echo()
        self.win3.move(0,0)
        self.win3.clrtobot()
        self.win3.addstr(0,0, prompt)
        string = self.win3.getstr(y,x)
        try:
            string = string.replace(',', '.')
            number = float(string)
        except ValueError:
            number = None
        curses.halfdelay(self.settings['halfdelay'])
        curses.noecho()
        return number

    def function(self, num=4):
        """Shortcut to different menus. Default is \"Reset\"
To add elements to menu, add functionality here, and add the menu element in
__init__ under 'self.menu' and 'self.lst'"""
        if num == 1:
            # Set voltage
            cmd = self.get_input(prompt='Enter voltage:')
            if not cmd:
                self.values['status'] = 'Illegal value: only numbers allowed'
            elif cmd >= 0 and cmd <= self.psc.V_max:
                self.psc.set_voltage(cmd)
                self.values['voltage_set'] = cmd
                #self.values['power_set'] = self.values['voltage_set']*self.values['current_set']
                self.values['status'] = 'Voltage set'
            else:
                self.values['status'] = 'Illegal number entered: out of range.'
            self.update_display()
        elif num == 2:
            # Set current
            cmd = self.get_input(prompt='Enter current:')
            if not cmd:
                self.values['status'] = 'Illegal value: only numbers allowed'
            elif cmd >= 0 and cmd <= self.psc.I_max:
                self.psc.set_current(cmd)
                self.values['current_set'] = cmd
                #self.values['power_set'] = self.values['voltage_set']*self.values['current_set']
                self.values['status'] = 'Current set'
            else:
                self.values['status'] = 'Illegal number entered: out of range.'
            self.update_display()
        elif num == 3:
            # Heat ramp
            self.run_ramp(fit=False)
        elif num == 4:
            # Reset power supply
            for i in ['current_set', 'voltage_set']:#, 'power_set']:
                self.values[i] = 0
            self.psc.reset()
            self.psc.output(True)
            self.values['status'] = 'Ready'
            self.update_display()
        elif num == 5:
            # Edit ramp options
            self.edit_parameters()
        elif num == 6:
            # Run ramp with fitted parameters
            self.run_ramp(fit=True)
        elif num == 0:
            # Close program
            self.values['status'] = 'Shutting down...'
            self.update_display()
            time.sleep(0.5)
            self.stop()

    def edit_parameters(self):
        """Function that handles editing parameters in program"""

        lst = ['Heat slope', 'standby current',
               'STOP current', 'STOP temp',
               'PID param [p/i/d]',
               'PS ramp voltage', 'PS ramp current',
               'PID delay (s)', 'PID tracker']
        defaults = [self.ramp['value'], self.ramp['standby current'],
                    self.ramp['stop current'], self.ramp['stop temperature'],
                    [self.calc.pid.pid_p, self.calc.pid.pid_i, self.calc.pid.pid_d],
                    self.ramp['voltage'], self.ramp['current'],
                    self.ramp['wait'], self.ramp['track']]
        self.win3.move(0,0)
        self.win3.clrtobot()
        box = 'Edit values below (submit with CTRL+G)\n'
        for i in range(len(lst)):
            box = box + '{}: {}\n'.format(lst[i], defaults[i])
        box = box.replace(',', '/')
        self.win3.addstr(0,0, box)
        contents = curses.textpad.Textbox(self.win3).edit()
        contents = contents.split('\n')
        for con in contents:
            text = ''
            try:
                text, value = con.split(':')
            except:
                continue

            # Slope of temperature ramp
            if text == lst[0]:
                try:
                    self.ramp['value'] = float(value)
                except ValueError:
                    continue

            # Standby current (value after heat ramp)
            elif text == lst[1]:
                try:
                    self.ramp['standby current'] = float(value)
                except ValueError:
                    continue

            # Stop criteria - current and temperature
            elif text == lst[2]:
                try:
                    self.ramp['stop current'] = float(value)
                except ValueError:
                    continue
            elif text == lst[3]:
                try:
                    self.ramp['stop temperature'] = float(value)
                except ValueError:
                    continue

            # PID parameters
            elif text == lst[4]:
                value = value.lstrip(' [').rstrip('] ')
                value = value.split('/')
                try:
                    p = float(value[0].replace(',', '.'))
                except ValueError:
                    #self.values['status'] = repr(value)
                    continue
                try:
                    i = float(value[1].replace(',', '.'))
                except ValueError:
                    #self.values['status'] = repr(value)
                    continue
                try:
                    d = float(value[2].replace(',', '.'))
                except ValueError:
                    #self.values['status'] = repr(value)
                    continue
                self.calc.pid.pid_p = p
                self.calc.pid.pid_i = i
                self.calc.pid.pid_d = d

            # Voltage ramp parameters
            elif text == lst[5]:
                value = value.lstrip(' [').rstrip('] ')
                value = value.split('/')
                #self.values['status'] = repr(value)
                try:
                    ramp_value = float(value[0].replace(',', '.'))
                    if ramp_value < 0:
                        #print(1)
                        continue
                except ValueError:
                    #print(2)
                    continue
                try:
                    ramp_type = int(value[1])
                    if not ramp_type in range(5):
                        #print(3)
                        continue
                except ValueError:
                    #print(4)
                    continue
                self.ramp['voltage'] = [ramp_value, ramp_type]
                #print(self.ramp['voltage'])
                self.psc.ramp_voltage(self.ramp['voltage'][0], program=self.ramp['voltage'][1])


            # Current ramp parameters
            elif text == lst[6]:
                value = value.lstrip(' [').rstrip('] ')
                value = value.split('/')
                try:
                    ramp_value = float(value[0].replace(',', '.'))
                    if ramp_value < 0:
                        continue
                except ValueError:
                    continue
                try:
                    ramp_type = int(value[1])
                    if not ramp_type in range(5):
                        continue
                except ValueError:
                    continue
                self.ramp['current'] = [ramp_value, ramp_type]
                self.psc.ramp_current(self.ramp['current'][0], program=self.ramp['current'][1])

            # Sleep/wait parameter
            elif text == lst[7]:
                try:
                    self.ramp['wait'] = float(value)
                except ValueError:
                    continue

            # Track values option
            elif text == lst[8]:
                try:
                    self.ramp['track'] = int(value)
                except ValueError:
                    continue

        defaults = [self.ramp['value'], self.ramp['standby current'],
                    self.ramp['stop current'], self.ramp['stop temperature'],
                    [self.calc.pid.pid_p, self.calc.pid.pid_i, self.calc.pid.pid_d],
                    self.ramp['voltage'], self.ramp['current'],
                    self.ramp['wait'], self.ramp['track']]
        self.win3.move(0,0)
        self.win3.clrtobot()
        box = ''
        for i in range(len(lst)):
            box = box + '{}: {}\n'.format(lst[i], defaults[i])
        box = box.replace(',', '/')
        self.win3.addstr(0, 0, box)
        self.win3.refresh()
                
        

    def run(self):
        """Main while loop (function) that receives input from user and handles
information accordingly """
        try:
            while not self.quit:
                # Wait for input from user (timeout: 'halfdelay')
                c = self.screen.getch()
                
                # Choose with keys and space/enter
                if c == 65 or c == 68: # KEY_UP or KEY_RIGHT
                    if self.cursor > 0:
                        self.cursor -= 1
                        self.update_menu()
                elif c == 66 or c == 67: # KEY_DOWN or KEY_LEFT
                    if self.cursor < len(self.menu.keys())-1:
                        self.cursor += 1
                        self.update_menu()
                elif c == 10 or c == 32: # SPACE or ENTER:
                    self.function(self.lst[self.cursor])
                # Choose with numbers
                elif c == ord('1'):
                    self.function(1)
                elif c == ord('2'):
                    self.function(2)
                elif c == ord('3'):
                    self.function(3)
                elif c == ord('4'):
                    self.function(4)
                elif c == ord('5'):
                    self.function(5)
                elif c == ord('6'):
                    self.function(6)
                elif c == ord('0') or c == ord('Q'): # Stop
                    self.function(0)
                else:
                    self.update_display()
        except:
            print('Exception in TUI loop')
            self.stop()
            raise


if __name__ == '__main__':
    # Initialize pullsocket
    pullsocket = DateDataPullSocket('omicron_heat_ramp_pull',
                                    CODENAMES,
                                    port=9001,
                                    )
    pullsocket.start()
    
    # Initalize power supply
    device = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'
    fug = FUGNTN140Driver(port=device, device_reset=True, V_max=12.5, I_max=8)
    fug.output(True)
    time.sleep(1)
    
    # Initalize power calculator (PID)
    #calculator = PowerCalculatorClassOmicron(ramp=1.0)
    #calculator.start()
    #time.sleep(1)

    # Initialize terminal user interface
    TUI = CursesTui(fug, pullsocket)
    TUI.start()
