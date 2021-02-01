print('Importing native modules...')
import os
import curses
import curses.textpad
import time
import logging
import json
import datetime
import threading

print('Importing numpy...')
import numpy as np

print('Importing user modules...')
from PyExpLabSys.drivers.fug import FUGNTN140Driver
from PyExpLabSys.common.sockets import DateDataPullSocket
from heat_ramp import PowerCalculatorClassOmicron
import fit_ramp
print('Imports complete')

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

DEFAULT_SETTINGS = {'name': 'HARDCODED SETTINGS',
                    'Description': '',
                    'heating rate': 0.5, # K/s
                    'standby current': 1.8, # A
                    'stop current': 5.5, # A
                    'stop temperature': 50, # Celcius
                    'pid': [0.06, 1e-05, 0.0], # [p, i, d]
                    'ramp voltage': [0, 0], # No limitations on voltage
                    'ramp current': [0, 0], # No limitations on current
                    'wait': 0.0, # No extra time [s] between PID loops
                    'track': 1, # Display PID info
}

def update_menu(window, cursor, options):
    window.move(0,0)
    window.clrtobot()
    for i, j in enumerate(options):
        if cursor == i:
            marker = curses.A_REVERSE
        else:
            marker = curses.A_NORMAL
        window.addstr(i,3, j, marker)
    window.refresh()

class CursesTui(threading.Thread):
    """ Interface for the power supply for Omicron TPD's """
    
    def __init__(self, powersupplyclass, pullsocket):
        threading.Thread.__init__(self)
        self.psc = powersupplyclass
        self.calc = PowerCalculatorClassOmicron(ramp=1.0)
        self.pullsocket = pullsocket
        # Setting parameters
        self.halfdelay = 1
        # Value parameters
        self.values = {}
        self.values['status'] = 'Starting'
        self.values['voltage_mon'] = 0
        self.values['voltage_set'] = 0
        self.values['current_mon'] = 0
        self.values['current_set'] = 0
        self.values['T_sample'] = None
        self.values['T_base'] = None
        self.values['temperature_set'] = None
        self.values['P_error'] = 0
        # Ramp parameters
        try:
            self.load_settings('default.settings')
        except IOError:
            self.values['status'] = 'No "default.settings" file found. Check settings.'
            self.settings = DEFAULT_SETTINGS
        self.update_settings()
        # Initialize screens and draw boxes
        self.screen = curses.initscr()
        curses.curs_set(0)
        curses.textpad.rectangle(self.screen, 0,0, 8,79)
        curses.textpad.rectangle(self.screen, 9,0, 20,30)
        curses.textpad.rectangle(self.screen, 9,32, 27,79)
        # Newwin options: lines, columns, start line, start column
        self.menu = {
            1: 'Set voltage',
            2: 'Set current',
            3: 'Run ramp',
            4: 'Reset',
            5: 'Configure settings',
            6: 'Fitted ramp',
            0: 'Quit (Q)',
        }
        self.win1 = curses.newwin(7,77, 1,1)
        self.win2 = curses.newwin(len(self.menu)+2,28, 10,1)
        self.win3 = curses.newwin(15,44, 10,33)
        self.screen.refresh()
        curses.cbreak()
        curses.noecho()
        curses.halfdelay(self.halfdelay)
        self.quit = False
        self.cursor = 4
        self.lst = [1, 2, 3, 4, 5, 6, 0]
        self.update_display()
        self.update_menu()

    def run_ramp(self, fit=False, limit_ramp=False):
        """Ramp function (PID controlled heating)"""
        
        self.values['status'] = 'Ramp running... (exit on "q")'
        self.update_display()
        if self.settings['track']:
            time_start = time.time()
            self.win3.clrtobot()
            self.win3.refresh()

        # Prepare ramp limitation
        self.psc.ramp_current(self.settings['ramp current'][0], program=self.settings['ramp current'][1])
        if limit_ramp:
            tau = 0.25
            averaging_time = 30.
            avg_N = int(averaging_time/tau)
            avg = [ tau * self.settings['ramp current'][0] ]
            avg = avg * avg_N
            avg_counter = 0
        else:
            new_ramp = self.settings['ramp current'][0]

        # Start PID calculator
        curses.halfdelay(1)
        self.calc.ramp = self.settings['heating rate']

        # Set the "zero" for the PID control
        LOGGER.warning('Starting ramp at {}'.format(datetime.datetime.now()))
        LOGGER.warning('Settings used is {}'.format(self.settings))
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
                setpoint = self.calc.get_setpoint()

            # Use fitted setpoint
            else:
                t_now = time.time() - t0
                self.calc.get_temperature()
                self.calc.values['setpoint'] = tset_start + t_now*0.5 # hardcoded ramp
                setpoint = local_calc.get_setpoint(t_now)
                if not setpoint is None:
                    setpoint = self.settings['stop current'] + 1

            # Break if current would be set too high
            if (setpoint >= self.settings['stop current']):
                self.values['status'] = 'Halt: Max current reached'
                self.update_display()
                break
            # Break if temperature gets too high
            elif (self.calc.values['temperature']  >= self.settings['stop temperature']):
                self.values['status'] = 'Halt: Max temperature reached'
                self.update_display()
                break
            # Implement new setpoint
            self.psc.set_current(setpoint)
            self.values['current_set'] = setpoint
            self.values['temperature_set'] = self.calc.values['setpoint']

            # Pause system to allow current to change
            time.sleep(self.settings['wait'])
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
            if self.settings['track']:
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
        self.psc.ramp_current(self.settings['ramp current'][0], program=2)
        self.psc.set_current(self.settings['standby current'])
        self.values['current_set'] = self.settings['standby current']
        self.values['status'] += ' - Ramp completed'
        self.update_display()
        curses.halfdelay(self.halfdelay)

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
        self.values['T_sample'] = self.calc.comms['temperature'].get_field('omicron_tpd_sample_temperature')[1]
        self.values['T_base'] = self.calc.comms['temperature'].get_field('omicron_tpd_temperature')[1]
        self.update_socket()

    def update_socket(self):
        """Write values to pullsocket """
        if self.calc:
            self.values['P_error'] = self.calc.pid.error[1]
        for codename in CODENAMES:
            self.pullsocket.set_point_now(codename, self.values[codename])

    def update_display(self):
        """Refreshes the window with values"""
        self.update_values()
        try:
            if self.values['T_sample'] is None:
                Tsample = '----'
            else:
                Tsample = self.values['T_sample']
            if self.values['T_base'] is None:
                Tbase = '----'
            else:
                Tbase = self.values['T_base']
            self.display = '' + \
                           'Status: {: <50s}\n'.format(self.values['status']) + \
                           '\n' + \
                           'Voltage setpoint:        Current setpoint:            Sample temperature\n' + \
                           ' {: <24f} {: <28f} {} C\n'.format(self.values['voltage_set'], self.values['current_set'], Tsample) + \
                           '\n' + \
                           'Voltage value:           Current value:               Base temperature\n' + \
                           ' {: <24f} {: <28f} {} C'.format(self.values['voltage_mon'], self.values['current_mon'], Tbase)
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
        self.win2.addstr(1,0, self.menu_win)
        self.win2.refresh()


    def function(self, num=4):
        """Shortcut to different menus. Default is \"Reset\"
To add elements to menu, add functionality here, and add the menu element in
__init__ under 'self.menu' and 'self.lst'"""
        if num == 1:
            # Set voltage
            cmd = self.get_input(prompt='Enter voltage:')
            if cmd is None:
                self.values['status'] = 'Illegal value: only numbers allowed'
            elif cmd >= 0 and cmd <= self.psc.V_max:
                self.psc.set_voltage(cmd)
                self.values['voltage_set'] = cmd
                self.values['status'] = 'Voltage set'
            else:
                self.values['status'] = 'Illegal number entered: out of range.'
            self.update_display()
        elif num == 2:
            # Set current
            cmd = self.get_input(prompt='Enter current:')
            if cmd is None:
                self.values['status'] = 'Illegal value: only numbers allowed'
            elif cmd >= 0 and cmd <= self.psc.I_max:
                self.psc.set_current(cmd)
                self.values['current_set'] = cmd
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
            self.configure_settings()
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
        defaults = [self.settings[i] for i in ['heating rate', 'standby current', 'stop current',
                                               'stop temperature', 'pid', 'ramp voltage', 'ramp current',
                                               'wait', 'track']]
        self.win3.move(0,0)
        self.win3.clrtobot()
        box = 'Edit values below (submit with CTRL+G)\n'
        for i in range(len(lst)):
            box = box + '{}: {}\n'.format(lst[i], defaults[i])
        box = box.replace(',', '/')
        curses.curs_set(1)
        self.win3.addstr(0,0, box)
        #tb = curses.textpad.Textbox(self.win3, insert_mode=True)
        tb = curses.textpad.Textbox(self.win3)
        contents = tb.edit()
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
                    self.settings['heating rate'] = float(value)
                except ValueError:
                    continue

            # Standby current (value after heat ramp)
            elif text == lst[1]:
                try:
                    self.settings['standby current'] = float(value)
                except ValueError:
                    continue

            # Stop criteria - current and temperature
            elif text == lst[2]:
                try:
                    self.settings['stop current'] = float(value)
                except ValueError:
                    continue
            elif text == lst[3]:
                try:
                    self.settings['stop temperature'] = float(value)
                except ValueError:
                    continue

            # PID parameters
            elif text == lst[4]:
                value = value.lstrip(' [').rstrip('] ')
                value = value.split('/')
                try:
                    p = float(value[0].replace(',', '.'))
                except ValueError:
                    continue
                try:
                    i = float(value[1].replace(',', '.'))
                except ValueError:
                    continue
                try:
                    d = float(value[2].replace(',', '.'))
                except ValueError:
                    continue
                self.settings['pid'] = [p, i, d]

            # Voltage ramp parameters
            elif text == lst[5]:
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
                self.settings['ramp voltage'] = [ramp_value, ramp_type]


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
                self.settings['ramp current'] = [ramp_value, ramp_type]

            # Sleep/wait parameter
            elif text == lst[7]:
                try:
                    self.settings['wait'] = float(value)
                except ValueError:
                    continue

            # Track values option
            elif text == lst[8]:
                try:
                    self.settings['track'] = int(value)
                except ValueError:
                    continue

        self.update_settings()
        defaults = [self.settings[i] for i in ['heating rate', 'standby current', 'stop current',
                                               'stop temperature', 'pid', 'ramp voltage', 'ramp current',
                                               'wait', 'track']]
        self.win3.move(0,0)
        self.win3.clrtobot()
        box = ''
        for i in range(len(lst)):
            box = box + '{}: {}\n'.format(lst[i], defaults[i])
        box = box.replace(',', '/')
        self.win3.addstr(0, 0, box)
        self.win3.refresh()
        curses.curs_set(0)


    def update_settings(self):
        """Apply settings dict to parameters"""
        self.calc.pid.pid_p, self.calc.pid.pid_i, self.calc.pid.pid_d = self.settings['pid']
        self.psc.ramp_voltage(self.settings['ramp voltage'][0], program=self.settings['ramp voltage'][1])
        self.psc.ramp_current(self.settings['ramp current'][0], program=self.settings['ramp current'][1])

    def load_settings(self, filename):
        """Load and apply settings from a file"""
        path = '_settings/'
        f = open(path+filename, 'r')
        try:
            settings = json.loads(f.readline())
        except ValueError:
            f.close()
            self.values['status'] = 'invalid settings file. Please check it'
            self.update_display()
            return
        self.settings = settings
        f.close()
        self.update_settings()

    def save_settings(self):
        """Save settings parameters to a file"""

        # Get filename as input
        while True:
            filename = self.get_input(y=5, prompt='Enter filename (".settings" will be appended). Leave empty to abort.', ret='text')
            if len(filename) == 0:
                self.values['status'] = 'Save settings aborted'
                return
            if filename[0].lower() not in '1234567890abcdefghijklmnopqrstuvwxyz':
                continue
            break
        if filename.endswith('.settings'):
            filename = filename.rstrip('.settings')
        self.settings['name'] = filename
        filename += '.settings'

        LOGGER.warning('filename: {}'.format(filename))

        # Get description as input
        description = self.get_input(y=6, prompt='Optional description (like temp range, sample type, ..). Leave empty to abort.', ret='text')
        if len(description) == 0:
            self.values['status'] = 'Save settings aborted'
            return
        self.settings['description'] = description
        LOGGER.warning('description: {}'.format(description))

        # Save to file
        f = open('_settings/' + filename, 'w')
        f.write(json.dumps(self.settings))
        f.close()
        self.values['status'] = 'Settings saved to "' + filename + '"'


    def configure_settings(self):
        """Save or load present settings."""
        self.values['status'] = 'Entered configure menu'
        cursor = 0
        options = ['back', 'configure', 'save', 'load']
        update_menu(self.win3, cursor, options)

        while True:
            # Wait for input from user (timeout: 'halfdelay')
            c = self.screen.getch()

            # Choose with keys and space/enter
            if c == 65 or c == 68: # KEY_UP or KEY_LEFT
                if cursor > 0:
                    cursor -= 1
                    update_menu(self.win3, cursor, options)
            elif c == 66 or c == 67: # KEY_DOWN or KEY_RIGHT
                if cursor < len(options)-1:
                    cursor += 1
                    update_menu(self.win3, cursor, options)
            elif c == 10 or c == 32: # SPACE or ENTER:
                selection = options[cursor]
                self.values['status'] = selection
                self.update_display()
                if selection == 'back':
                    break
                elif selection == 'configure':
                    self.edit_parameters()
                elif selection == 'save':
                    self.save_settings()
                elif selection == 'load':
                    self.choose_load_file()
                break
        self.win3.move(0,0)
        self.win3.clrtobot()
        self.win3.refresh()


    def choose_load_file(self):
        """Get a list of settings files to choose from"""
        files = [x for x in os.listdir('_settings') if x.endswith('.settings')]
        files.sort()
        num_files = len(files)
        if num_files == 0:
            self.win3.move(0,0)
            self.win3.clrtobot()
            self.win3.addstr(0,0, 'No settings files present')
            self.win3.refresh()
            time.sleep(2.5)
            return

        # Make page of loadable files
        max_lines = 8
        max_line_counter = max_lines - 1
        max_pages = int(np.ceil(float(num_files)/max_lines))
        max_page_counter = max_pages - 1
        page_counter = 0
        cursor = 0
        update_menu(self.win3, cursor=cursor, options=files[0:max_lines])
        self.values['status'] = 'Page {} of {}'.format(page_counter+1, max_pages)
        self.update_display()
        while True:
            # Wait for input from user (timeout: 'halfdelay')
            c = self.screen.getch()

            # Choose with keys and space/enter
            if c == 65 or c == 68: # KEY_UP or KEY_LEFT
                if cursor > 0:
                    cursor -= 1
                elif cursor == 0 and page_counter > 0:
                    page_counter -= 1
                    cursor = max_lines - 1
                    self.values['status'] = 'Page {} of {}'.format(page_counter+1, max_pages)
                    self.update_display()
            elif c == 66 or c == 67: # KEY_DOWN or KEY_RIGHT
                if cursor < max_line_counter:
                    if cursor + page_counter*max_lines < num_files - 1:
                        cursor += 1
                elif cursor == max_line_counter and page_counter < max_page_counter:
                    page_counter += 1
                    cursor = 0
                    self.values['status'] = 'Page {} of {}'.format(page_counter+1, max_pages)
                    self.update_display()
            elif c == 10 or c == 32: # SPACE or ENTER:
                filename = files[page_counter*max_lines + cursor]
                self.values['status'] = filename
                self.update_display()
                self.load_settings(filename)
                break
            elif c == ord('q'):
                break
            selection = page_counter * max_lines
            update_menu(self.win3, cursor=cursor, options=files[selection:selection+max_lines])
        self.win3.move(0,0)
        self.win3.clrtobot()
        self.win3.refresh()


    def get_input(self, y=1, x=2, prompt='Enter value:', ret='number'):
        """Receives an input value from user and returns a float."""
        curses.echo()
        self.win3.move(0,0)
        self.win3.clrtobot()
        self.win3.addstr(0,0, prompt)
        string = self.win3.getstr(y,x)
        string = string.decode()
        if ret == 'number':
            try:
                string = string.replace(',', '.')
                string = float(string)
            except ValueError:
                string = None
        elif ret == 'text':
            pass
        curses.halfdelay(self.halfdelay)
        curses.noecho()
        return string


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
