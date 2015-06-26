""" Tui for controling the temperature of the high pressure
cell of stm312"""
# -*- coding: utf-8 -*-

import time
import threading
import curses
import socket
from datetime import datetime
import PyExpLabSys.drivers.cpx400dp as CPX
#from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.loggers import ContinuousLogger
import credentials

EXCCEPTION = None
log = open('error_log.txt', 'w')

#output = 'print'
#output = 'curses'

db_logger = ContinuousLogger(table='dateplots_stm312',
                             username=credentials.user,
                             password=credentials.passwd,
                             measurement_codenames=['stm312_hpc_psu_voltage',
                                                    'stm312_hpc_psu_current'])

class PID(object):
    """Implementation of a PID routine
    """
    def __init__(self, case=None):
        """The input parameter case is used to simplify that several
        system is sharing the software, each with it own parametors."""
        if case == None:
            self.gain = {'Kp':0.15,
                         'Ki':0.0025,
                         'Kd':0.0,
                         'Pmax':100.0,
                         'Pmin':0.0}
        elif case == 'stm312 hpc':
            self.gain = {'Kp':1.7,
                         'Ki':0.015,
                         'Kd':0.0,
                         'Pmax':60.0,
                         'Pmin':0.0}
        #Provid a starting setpoit to ensure that the PID does not
        #apply any power before an actual setpoit is set.
        self.setpoint = -9999
        #self.Kp = self.gain['Kp']
        #self.Ki = self.gain['Ki']
        #self.Kd = self.gain['Kd']
        self.pid_coef = {'p': self.gain['Kp'],
                         'i': self.gain['Ki'],
                         'd': self.gain['Kd']}
        #self.Pmax = self.gain['Pmax']
        #self.Pmin = self.gain['Pmin']
        # stating power values
        self.power = {'current': 0.0,
                      'prev': 0.0,
                      'max': self.gain['Pmax'],
                      'min': self.gain['Pmin']}
        #self.initialize()
        self.time = {'current': time.time(),
                     'prev': time.time()}
        self.error = {'current': 0.0,
                      'prev': 0.0}
        self.prev_err = 0.0
        #self.prev_power = 0.0

        self.cumulated = {'p': 0.0,
                          'i': 0.0,
                          'd': 0.0}

    def initialize(self,):
        """ Initialize delta t variables. """
        self.error = {'current': 0.0,
                      'prev': 0.0}
        self.cumulated = {'p': 0.0,
                          'i': 0.0,
                          'd': 0.0}

    def reset_integrated_error(self):
        """ Reset the I value, integrated error. """
        #self.Ci = 0
        self.cumulated['i'] = 0.0

    def update_setpoint(self, setpoint):
        """ Update the setpoint."""
        self.setpoint = setpoint
        return setpoint

    def get_new_Power(self, T):
        """ Get new power for system, P_i+1
        :param T: Actual temperature
        :type T: float
        :returns: best guess of need power
        :rtype: float
        """
        self.error['current'] = self.setpoint - T
        #self.currtm = time.time()
        self.time['current'] = time.time()
        #dt = self.currtm - self.prevtm
        diff_temp = self.time['current'] - self.time['prev']
        diff_error = self.error['current'] - self.error['prev']
        # Calculate proportional gain.
        self.cumulated['p'] = self.error['current']

        # Calculate integral gain, including limits
        if self.power['prev'] > self.power['max'] and self.error['current'] > 0:
            pass
        elif self.power['prev'] < self.power['min'] and self.error['current'] < 0:
            pass
        else:
            self.cumulated['i'] += self.error['current'] * diff_temp
        # Calculate derivative gain.
        if diff_temp > 0:
            self.cumulated['d'] = diff_error/diff_temp
        else:
            self.cumulated['d'] = 0

        # Adjust times, and error for next iteration.
        #self.prevtm = self.currtm
        self.time['prev'] = self.time['current']
        self.error['prev'] = self.error['current']

        #Calculate Output.
        self.power['current'] = 0
        for key, value in self.pid_coef.iteritems():
            self.power['current'] += value*self.cumulated[key]
        #P = self.Kp * self.Cp + \
        #    self.Ki * self.Ci + \
        #    self.Kd * self.Cd
        self.power['prev'] = self.power['current']

        #Check if output is valid.
        if self.power['current'] > self.power['max']:
            self.power['current'] = self.power['max']
        if self.power['current'] < 0:
            self.power['current'] = 0
        return self.power['current']

class ValueLogger(object):
    """ Read a continuously updated values and decides
    whether it is time to log a new point """
    def __init__(self, maximumtime=600,
                 comp_type='lin',
                 comp_val=1,
                 codename=None):
        self.maximumtime = maximumtime
        self.compare = {'type':comp_type, 'val':comp_val}
        self.codename = codename

        self.value = 0.0
        self.last = {'time':0.0, 'val':0.0}

        self.status = {'trigged':False}

    def add_logger(self, db_logger):
        self.db_logger = db_logger

    def trigger(self, value):
        self.value = value
        time_trigged = ((time.time() - self.last['time']) > self.maximumtime)
        if self.compare['type'] == 'lin':
            val_trigged = not (self.last['val'] - self.compare['val'] <
                               self.value <
                               self.last['val'] + self.compare['val'])
        elif self.compare['type'] == 'log':
            val_trigged = not (self.last['val'] * (1 - self.compare['val']) <
                               self.value <
                               self.last['val'] * (1 + self.compare['val']))
        if (time_trigged or val_trigged) and (self.value > 0):
            self.status['trigged'] = True
            self.last['time'] = time.time()
            self.last['val'] = self.value
            self.log_value()

    def log_value(self,):
        if self.status['trigged'] and self.codename != None:
            self.db_logger.enqueue_point_now(self.codename, self.value)
            self.status['trigged'] = False

class CursesTui(threading.Thread):
    """ the display TUI for changing and chowing the temperature of the high
    pressure cell"""
    def __init__(self, powercontrolclass):
        threading.Thread.__init__(self)
        self.pcc = powercontrolclass
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)
        self.time = time.time()
        self.countdown = False
        self.last_key = None
        self.running = True

    def run(self,):
        while self.running:
            time.sleep(0.1)
            try:
                self.screen.addstr(3, 2,
                                   "Power Supply for HPC " \
                                   "stm312, ID: {}".format(
                                    self.pcc.status['ID']))
            except Exception, e:
                self.screen.addstr(3, 2,
                                   "Power Supply for HPC stm312," \
                                   " ID: {}".format(e))
            if self.pcc.status['Output']:
                self.screen.addstr(4, 2,
                                   "Power Output: {}    ".format(
                                       self.pcc.status['Output']))
                self.screen.addstr(5, 2,
                                   "Control mode: {}    ".format(
                                       self.pcc.status['Mode']))
            try:
                self.screen.addstr(6, 2,
                                   "Current:    {0:+.2f} A  -  " \
                                   "{1:+.2f} A     ".format(
                                       self.pcc.status['Current'],
                                       self.pcc.status['Wanted Current']))
                self.screen.addstr(7, 2,
                                   "Voltage:    {0:+.2f} V  -  " \
                                   "{1:+.2f} V     ".format(
                                       self.pcc.status['Voltage'],
                                       self.pcc.status['Wanted Voltage']))
                self.screen.addstr(8, 2,
                                   "Power:      {0:+.2f} W  -  " \
                                   "{1:+.2f} W     ".format(
                                       self.pcc.status['Actual Power'],
                                       self.pcc.status['Wanted Power']))
                self.screen.addstr(9, 2, "Resistance: {0:+.3f} Ohm     ".format(
                        self.pcc.status['Resistance']))
                self.screen.addstr(11, 2,
                                   "Temperature: {0:+.2f}C" \
                                   "     ".format(
                                       self.pcc.status['Temperature']))
                try:
                    self.screen.addstr(12, 2,
                                       "Setpoint: {0:+.2f} {}" \
                                       "        ".format(
                                           self.pcc.status['Setpoint'],
                                           self.pcc.status['Setpoint unit']))
                except:
                    self.screen.addstr(12, 2, "Setpoint: {0:+.2f}".format(
                            self.pcc.status['Setpoint']))
            except Exception as exception:
                global EXCEPTION
                EXCEPTION = exception
            if self.pcc.status['error'] != None:
                self.screen.addstr(17, 2,
                                   "Latest error message: {}" \
                                   ", at time: {}".format(
                                       self.pcc.status['error'],
                                       self.pcc.status['error time']-self.time))
            #if self.pcc.status['error'] != None:
            self.screen.addstr(16, 2,
                               "Runtime: {0:.0f}s     ".format(
                                   time.time() - self.time))
            if self.countdown:
                self.screen.addstr(17, 2,
                                   "Time until shutdown: {0:.0f} s " \
                                   "( {1:.1f} h )              ".format(
                                       (self.countdown_end_time - time.time()),
                                       (self.countdown_end_time - time.time())/3600.0 ))
                if time.time() > self.countdown_end_time:
                    self.pcc.change_mode('Voltage Control')
                    self.pcc.zero_setpoint()
                    #self.pcc.OutputOff()
                    self.countdown = False
            else:
                self.screen.addstr(17, 2,
                                   "Time until shutdown: -                ")
            if self.last_key != None:
                self.screen.addstr(24, 2,
                                   " Latest key: ".format(self.last_key))
            self.screen.addstr(21, 2,
                               "q: quit program, " \
                               "z: increas setpoint, " \
                               "x: decrease setpoint     ")
            self.screen.addstr(22, 2,
                               "t: PID temperature control, " \
                               "i, fixed current, " \
                               "v: fixed voltage, " \
                               "p: fixed power     ")
            self.screen.addstr(23, 2,
                               "3: shutdown in 3h, " \
                               "8: shutdown -900s, " \
                               "9: shutdown +900s")

            n = self.screen.getch()
            if n == ord("q"):
                self.pcc.running = False
                self.running = False
                self.last_key = chr(n)
            elif n == ord('t'):
                self.pcc.change_mode('Temperature Control')
                self.last_key = chr(n)
            elif n == ord('i'):
                self.pcc.change_mode('Current Control')
                self.last_key = chr(n)
            elif n == ord('v'):
                self.pcc.change_mode('Voltage Control')
                self.last_key = chr(n)
            elif n == ord('p'):
                self.pcc.change_mode('Power Control')
                self.last_key = chr(n)
            elif n == ord('z'):
                self.pcc.increase_setpoint()
                self.last_key = chr(n)
            elif n == ord('x'):
                self.pcc.decrease_setpoint()
                self.last_key = chr(n)
            elif n == ord('3'):
                self.countdown = True
                self.countdown_end_time = time.time() + 3*3600.0 # sencond
                self.last_key = chr(n)
            elif n == ord('8') and self.countdown == True:
                self.countdown_end_time -= 900
                self.last_key = chr(n)
            elif n == ord('9') and self.countdown == True:
                self.countdown_end_time += 900
                self.last_key = chr(n)
            self.screen.refresh()
        time.sleep(5)
        self.stop()
        #print EXCEPTION

    def stop(self):
        self.pcc.stop()
        #print(str(self.running))
        #print(str(self.pcc.running))
        #print(str(self.pcc.temp_class.running))
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()

#==============================================================================
#def sqlTime():
#    sqltime = datetime.now().isoformat(' ')[0:19]
#    return sqltime
#==============================================================================

#==============================================================================
# def sqlInsert(query):
#     try:
#         cnxn = MySQLdb.connect(
#             host="servcinf",
#             user="stm312",
#             passwd="stm312",
#             db="cinfdata")
#         cursor = cnxn.cursor()
#     except:
#         print("Unable to connect to database")
#         return()
#     try:
#         cursor.execute(query)
#         cnxn.commit()
#     except:
#         print "SQL-error, query written below:"
#         print query
#    cnxn.close()
#    return query
#==============================================================================    

def network_comm(host, port, string):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(string + "\n", (host, port))
        received = sock.recv(1024)
    except:
        received = ''
    return received

def read_hp_temp():
    data = 'stm312_hpc_temperature#raw'
    host = '127.0.0.1'
    port = 9000
    #received = network_comm(host, port, data)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.2)
    sock.sendto(data, (host, port))
    received = sock.recv(1024)
    temp = float(received[received.find(',')+1:])
    return temp

def read_setpoint():
    """Read the setpoint from socket."""
    received = network_comm('rasppi19', 9990, 'read_setpoint')
    temp = float(received)
    return(temp)

def write_setpoint(setpoint):
    """Write setpoint to socket."""
    #print "write_setpoint {}".format(setpoint)
    received = network_comm('rasppi19', 9990, 'set_setpoint '+str(setpoint))
    #temp = float(received)
    return received

class TemperatureClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.temperature = -999
        self.running = True
        self.error = False
        self.debug_level = 0
        self.error_count = 0

    def run(self):
        while self.running:
            #data_temp = 'T1#raw'
            #sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            #sock.settimeout(1)
            try:
                #sock.sendto(data_temp, ('localhost', 9001))
                #received = sock.recv(1024)
                #self.temperature = float(received[received.find(',') + 1:])
                self.temperature = float(read_hp_temp())
                self.error_count = 0
            except:
                self.error = True
                self.error_count += 1
            if self.debug_level > 0:
                print(str(self.temperature))
            #temperature = self.temperature
            time.sleep(0.25)
    def stop(self,):
        self.running = False

class PowerControlClass(threading.Thread):
    def __init__(self):#,datasocket,pushsocket
        #self.datasocket = datasocket
        #self.pushsocket = pushsocket
        threading.Thread.__init__(self)
        write_setpoint(0.0)
        #self.PowerCalculatorClass = PID_class
        self.running = True
        self.status = {}
        self.status['Mode'] = 'Voltage Control' #, 'Power Control'

        self.logger = False
        self.init_status()
        self.init_PID_class()
        #self.init_temp_class()
        self.init_heater_class()

    def init_status(self,):
        self.status['error'] = None
        self.status['Setpoint'] = 0.0
        self.status['Setpoint unit'] = "au"

        self.status['Current'] = 0.0
        self.status['Wanted Current'] = 0.0

        self.status['Voltage'] = 0.0
        self.status['Wanted Voltage'] = 0.0

        self.status['Actual Power'] = 0.0
        self.status['Wanted power'] = 0.0

        self.status['Resistance'] = 1.0

        self.status['ID'] = '0'

    def init_temp_class(self, temp_class):
        self.temp_class = temp_class

    def init_PID_class(self,):
        self.power = 0.0
        self.setpoint = 0.0
        self.pid = PID(case='stm312 hpc')
        #self.pid.Kp = 0.5
        #self.pid.Ki = 0.01
        #self.pid.Kd = 0.0
        #self.pid.Pmax = 90.0
        self.pid.update_setpoint(self.setpoint)
        self.status['Wanted Power'] = self.power
        self.status['Setpoint'] = self.setpoint

    def init_heater_class(self,):
        dev_port = '/dev/serial/by-id/usb-TTI_CPX400_Series_PSU_C2F9545A-if00'
        self.heater = CPX.CPX400DPDriver(1, interface='serial', device=dev_port)
        self.status['ID'] = self.heater.read_software_version()
        print 'ID: ' + self.status['ID']
        #print 'Type: ' + type(self.status['ID'])

    def init_logger(self, db_logger):
        self.db_logger = db_logger
        self.valuelogger = {}
        self.valuelogger['Current'] = ValueLogger(maximumtime=600,
                                                  comp_type='lin',
                                                  comp_val=0.2,
                                                  codename='stm312_hpc_psu_current')
        self.valuelogger['Voltage'] = ValueLogger(maximumtime=600,
                                                  comp_type='lin',
                                                  comp_val=0.2,
                                                  codename='stm312_hpc_psu_voltage')
        self.valuelogger['Current'].add_logger(self.db_logger)
        self.valuelogger['Voltage'].add_logger(self.db_logger)
        self.logger = True

    def init_resistance(self,):
        self.heater.set_voltage(2)
        self.heater.output_status(on=True)
        time.sleep(1)
        I_calib = self.heater.read_actual_current()
        self.heater.output_status(on=False)
        self.R_calib = 2.0/I_calib

    def OutputOn(self,):
        """Set Output to On."""
        self.status['Output'] = True
        self.heater.output_status(on=True)

    def OutputOff(self,):
        """Set output to Off."""
        self.status['Output'] = False
        self.heater.output_status(on=False)

    def update_output(self,):
        self.status['Current'] = self.heater.read_actual_current()
        self.status['Voltage'] = self.heater.read_actual_voltage()
        self.status['Actual Power'] = self.status['Current'] * self.status['Voltage']
        self.status['Resistance'] = self.status['Voltage'] / self.status['Current']
        if not 0.4 < self.status['Resistance'] < 2.5:
            self.status['Resistance'] = 1.0
        
    def change_setpoint(self, setpoint):
        """Change the setpoint."""
        try:
            write_setpoint(setpoint)
        except:
            self.status['error'] = 'COM error with socket server'
            self.status['error time'] = time.time()
        self.status['Setpoint'] = read_setpoint()

    def increase_setpoint(self,):
        """Increment setpoint."""
        setpoint = read_setpoint()
        if self.status['Mode'] == 'Temperature Control':
            setpoint += 1
        elif self.status['Mode'] in ['Power Control', 'Current Control', 'Voltage Control']:
            setpoint += 0.1
        self.change_setpoint(setpoint)

    def decrease_setpoint(self,):
        """Decrement setpoint."""
        setpoint = read_setpoint()
        if self.status['Mode'] == 'Temperature Control':
            setpoint -= 1
        elif self.status['Mode'] in ['Power Control', 'Current Control', 'Voltage Control']:
            setpoint -= 0.1
        self.change_setpoint(setpoint)

    def zero_setpoint(self,):
        """Set setpoint to Zero."""
        self.change_setpoint(0.0)

    def change_mode(self, new_mode):
        """Change the mode between:
        Temperature, Power, Voltage, and Current."""
        if new_mode in ['Temperature Control',
                        'Power Control',
                        'Current Control',
                        'Voltage Control']:
            if new_mode in ['Power Control',
                            'Current Control',
                            'Voltage Control']:
                self.change_setpoint(self.status['Voltage'])
            elif new_mode in ['Power Control',]:
                self.change_setpoint(self.status['Actual Power'])
            elif new_mode in  ['Temperature Control']:
                self.change_setpoint(self.temp_class.temperature)
                self.pid.initialize()
            self.status['Mode'] = new_mode

            if new_mode in ['Temperature Control',]:
                self.status['Setpoint unit'] = 'degC'
            elif new_mode in ['Power Control',]:
                self.status['Setpoint unit'] = 'W'
            elif new_mode in ['Current Control',]:
                self.status['Setpoint unit'] = 'A'
            elif new_mode in ['Voltage Control',]:
                self.status['Setpoint unit'] = 'V'
        else:
            self.status['error'] = 'Mode does not exsist'
            self.status['error time'] = time.time()

    def run(self,):
        self.heater.set_voltage(0)
        self.OutputOn()
        while self.running:
            self.status['Setpoint'] = read_setpoint()
            self.status['Temperature'] = self.temp_class.temperature
            if self.status['Mode'] == 'Temperature Control':
                self.pid.update_setpoint(self.status['Setpoint'])
                self.status['Wanted Power'] = self.pid.get_new_Power(self.status['Temperature'])
                self.status['Wanted Voltage'] = ( self.status['Wanted Power'] * self.status['Resistance'] )**0.5
            elif self.status['Mode'] == 'Power Control':
                if self.status['Setpoint'] > 0 or self.status['Setpoint'] < 100:
                    self.status['Wanted Power'] = self.status['Setpoint']
                    self.status['Wanted Voltage'] = ( self.status['Wanted Power'] * self.status['Resistance'] )**0.5
            elif self.status['Mode'] == 'Current Control':
                if self.status['Setpoint'] > 0 or self.status['Setpoint'] < 10:
                    self.status['Wanted Current'] = self.status['Setpoint']
                    self.status['Wanted Voltage'] = self.status['Resistance'] * self.status['Wanted Current']
            elif self.status['Mode'] == 'Voltage Control':
                if self.status['Setpoint'] > 0 or self.status['Setpoint'] < 10:
                    self.status['Wanted Voltage'] = self.status['Setpoint']
            time.sleep(1)
            try:
                self.heater.set_voltage(self.status['Wanted Voltage'])
                if self.heater.debug:
                    raise serial.serialutil.SerialException
            except serial.serialutil.SerialException:
                self.init_heater()
            self.update_output()
            if self.logger == True:
                self.valuelogger['Current'].trigger(self.status['Current'])
                self.valuelogger['Voltage'].trigger(self.status['Voltage'])
        self.pid.update_setpoint(-200)
        self.OutputOff()
        self.stop()

    def stop(self,):
        """Stop function."""
        self.OutputOff()
        self.running = False
        try:
            self.temp_class.stop()
        except:
            pass


if __name__ == '__main__':
    print('Program start')
    #classes:
    TempClass = TemperatureClass()
    TempClass.start()
    time.sleep(2)

    pcc = PowerControlClass()#datasocket,pushsocket
    pcc.init_temp_class(TempClass)
    pcc.init_logger(db_logger)
    pcc.start()
    
    time.sleep(2)
    tui = CursesTui(pcc)
    tui.daemon = True
    tui.start()
