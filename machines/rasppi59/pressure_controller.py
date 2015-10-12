""" Pressure and temperature logger """
# pylint: disable=C0301,R0904, C0103

import threading
import time
import logging
import socket
import curses

import json

from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
#from PyExpLabSys.common.sockets import LiveSocket

""" driver """
import PyExpLabSys.drivers.mks_925_pirani as mks_pirani
import PyExpLabSys.drivers.mks_pi_pc as mks_pipc

import credentials

#name = 'stm312 HPC pressure'
#codenames = ['pressure','setpoint']
#socket = DateDataPullSocket(name, codenames)


db_logger_stm312 = ContinuousLogger(table='dateplots_stm312',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=['stm312_hpc_pressure_controller','stm312_pirani'])
#db_logger_ocs = ContinuousLogger(table='dateplots_oldclustersource',
#                                 username='dummy',
#                                 password='dummy',
#                                 measurement_codenames = ['pressure'])


class ValueLogger(object):
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
        if (time_trigged or val_trigged) and (self.value > -1):
            self.status['trigged'] = True
            self.last['time'] = time.time()
            self.last['val'] = self.value
            self.log_value()

    def log_value(self,):
        if self.status['trigged'] and self.codename != None:
            self.db_logger.enqueue_point_now(self.codename, self.value)
            self.status['trigged'] = False


class CursesTui(threading.Thread):
    def __init__(self, pressure_control):#, pirani, baratron, pullsocket):
        threading.Thread.__init__(self)
        #self.pullsocket = pullsocket
        self.pc = pressure_control
        #self.pirani = pirani
        #self.baratron = baratron
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)
        self.time = time.time()
        self.countdown = False
        self.last_key = None
        self.temp_key = None
        self.running = True
        
    def run(self,):
        while self.running:
            time.sleep(0.1)
            try:
                self.screen.addstr(3, 2, "Pressure Controller for HPC stm312,")# ID: {}".format(self.pc.status['ID']))
                #self.screen.addstr(4, 2, "Pirani for old cluster source")
            except Exception, e:
                self.screen.addstr(3, 2, "Pressure Controller for HPC stm312, {}".format(e))# ID: {}".format(self.pc.status['ID']))
                #self.screen.addstr(4, 2, "Pirani for old cluster source, {}".format(e))
                pass
            try:
                self.screen.addstr(6, 2, "HPC pressure, pressure control:     {0:+.1f}mbar     ".format(self.pc.pressure))
                self.screen.addstr(7, 2, "HPC pressure, setpoint:             {0:+.1f}mbar     ".format(self.pc.setpoint))
            except Exception, e:
                self.screen.addstr(6, 2, "HPC pressure, pressure control:     {}               ".format(e))
                self.screen.addstr(7, 2, "HPC pressure, setpoint:             {}               ".format(e))
            #try:
            #    self.screen.addstr(10, 2, "Old cluster source pirani:         {0:+.5f}mbar     ".format(self.pirani.pressure))
            #except Exception, e:
            #    self.screen.addstr(10, 2, "Old cluster source pirani:         {}               ".format(e))
            #try:
            #    self.screen.addstr(11, 2, "HPC pressure, baratron:            {0:+.5f}mbar     ".format(self.baratron.pressure))
            #except Exception, e:
            #    self.screen.addstr(11, 2, "HPC pressure, baratron:            {}               ".format(e))
            if self.pc.ERROR != None:
                self.screen.addstr(10, 2, "Latest error message: {}        ".format(self.pc.ERROR))
            #if self.pirani.ERROR != None:
            #    self.screen.addstr(13, 2, 'Latest error message: ' + str(self.pirani.ERROR))# + ' at time: ' + str(self.pcc.status['error time']))
            self.screen.addstr(11, 2, "Runtime: {0:.0f}s     ".format(time.time() - self.time))
            if self.last_key != None:
                self.screen.addstr(13, 2, " Latest key: {}  pressed key: {}     ".format(self.last_key, self.temp_key))
            self.screen.addstr(14, 2, "q: quit program           ")
            self.screen.addstr(15, 2, "z: increment setpoint     ")
            self.screen.addstr(16, 2, "x: decrement setpoint     ")
            #self.screen.addstr(22, 2, "t: PID temperature control, i, fixed current, v: fixed voltage, p: fixed power     ")
            
            n = self.screen.getch()
            if isinstance(n, int) and n > 0:
                self.temp_key = n
            if n == ord("q"):
                self.pc.running = False
                #self.pirani.running = False
                self.running = False
                self.last_key = chr(n)
            elif n == ord('z'):
                self.pc.increment_setpoint()
                self.last_key = chr(n)
            elif n == ord('x'):
                self.pc.decrement_setpoint()
                self.last_key = chr(n)
            """elif n == ord('v'):
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
            """
            self.screen.refresh()
        time.sleep(5)
        self.stop()
        
    def stop(self):
        print('Tui is stopping')
        try:
            self.pc.stop()
        except Exception, e:
            print(e)
            pass
        try:
            self.pirani.stop()
        except Exception, e:
            print(e)
            pass
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()

class PcClass(threading.Thread):
    """ Analog reader """
    def __init__(self):
        threading.Thread.__init__(self)
        ports = {}
        ports[0] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTXQCCIT-if00-port0'
        ports[1] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTXQNRNZ-if00-port0' #used by other
        ports[2] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTXQQ07N-if00-port0'
        ports[3] = '/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTWR5F6W-if00-port0' #used by other
        port = ports[2]
        self.pc = mks_pipc.Mks_Pi_Pc(port = port)
        self.pressure = None
        self.setpoint = 200
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False
        self.running = True
        self.ERROR = None
        self.socket_avalible = False
        self.db_logger_avalible = False

    def add_socket_server(self,pullsocket,pushsocket):
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.socket_avalible = True

    def add_logger(self,db_logger):
        self.db_logger = db_logger
        self.valuelogger = ValueLogger(maximumtime=600,
                                       comp_type='lin',
                                       comp_val=1.0,
                                       codename='stm312_hpc_pressure_controller')
        self.valuelogger.add_logger(self.db_logger)
        self.db_logger_avalible = True
    
    def read_pressure(self):
        """ Read the pressure """
        return(self.pressure)

    def read_setpoint(self):
        """ Read the setpoint """
        return(self.setpoint)

    def increment_setpoint(self,):
        self.update_setpoint(self.setpoint + 10)
        #self.setpoint += 10
        #self.set_setpoint(self.setpoint)
        return(True)
    
    def decrement_setpoint(self,):
        self.update_setpoint(self.setpoint - 10)
        #self.set_setpoint(self.setpoint)
        return(True)

    def set_setpoint(self, setpoint):
        """ Set the setpoint """
        self.setpoint = int(setpoint)
        try:
            self.pc.set_setpoint(self.setpoint)
        except Exception, e:
            self.ERROR = e
        if self.socket_avalible:
            self.pullsocket.set_point_now('setpoint',self.setpoint)
        return(True)

    def update_setpoint(self, setpoint=None):
        """ Update the setpoint """
        self.setpoint = setpoint
        if self.socket_avalible:
            self.pullsocket.set_point_now('setpoint', setpoint)
        return setpoint

    def run(self):
        sp_updatetime = 0
        while self.running:
            time.sleep(0.5)
            self.pressure = self.pc.read_pressure()
            #print self.pressure
            self.pc.set_setpoint(self.setpoint)
            if self.socket_avalible:
                self.pullsocket.set_point_now('pressure',self.pressure)
            #self.update_setpoint()
            try:
                if self.socket_avalible:
                    setpoint = self.pushsocket.last[1]['setpoint']
                    new_update = self.pushsocket.last[0]
                    self.message = str(new_update)
                else:
                    setpoint = None
            except (TypeError, KeyError): # Setpoint has never been sent
                setpoint = None
            if ((setpoint is not None) and
                (setpoint != self.setpoint) and (sp_updatetime < new_update)):
                self.update_setpoint(setpoint)
                sp_updatetime = new_update
            if self.db_logger_avalible:
                self.valuelogger.trigger(self.pressure)
        self.stop()
        
    def stop(self,):
        self.running = False
        try:
            self.db_logger.stop()
        except:
            pass
        try:
            self.pullsocket.stop()
            self.pushsocket.stop()
        except:
            pass
        #self.socket.stop()
        print('PcClass is stopping')


class PiraniClass(threading.Thread):
    """ Pressure reader """
    def __init__(self):
        threading.Thread.__init__(self)
        port = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'
        self.pirani = mks_pirani.mks_comm(port = port)
        self.pressure = None
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False
        self.running = True
        self.ERROR = None
        self.socket_avalible = False
        self.db_logger_avalible = False

    def add_logger(self,db_logger):
        self.db_logger = db_logger
        self.valuelogger = ValueLogger(maximumtime=600,
                                       comp_type='log',
                                       comp_val=1.5,
                                       codename='stm312_pirani')
        self.valuelogger.add_logger(self.db_logger)
        self.db_logger_avalible = True

    def read_pressure(self):
        """ Read the pressure """
        return(self.pressure)

    def run(self):
        while self.running:
            time.sleep(1)
            try:
                self.pressure = float(self.pirani.read_pressure())
            except Exception, e:
                self.ERROR = e
            if self.db_logger_avalible:
                self.valuelogger.trigger(self.pressure)
        self.stop()

    def stop(self,):
        self.running = False
        try:
            self.db_logger.stop()
        except:
            pass
        print('PiraniClass is stopping')

class Baratron(threading.Thread):
    def __init__(self,):
        threading.Thread.__init__(self)
        self.running = True
        self.pressure = -1.0
        self.address_port = ('rasppi56', 9000)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        pass
    def read_pressure(self,):
        self.sock.sendto('stm312_hpc_baratron#json', self.address_port)
        answer = self.sock.recvfrom(1024)
        print answer
        pressure_time, pressure = json.loads(answer[0])
        self.pressure = pressure
        return self.pressure
    def run(self,):
        while self.running:
            time.sleep(1)
            self.read_pressure()
#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)

#pc_measurement = PcClass()
#pc_measurement.start()

#pressure_measurement = PiraniClass()
#pressure_measurement.start()

#time.sleep(2)

"""
datasocket = DateDataPullSocket(['pirani', 'pc'], timeouts=[1.0, 1.0])
datasocket.start()

db_logger = ContinuousLogger(table='dateplots_stm312', username='stm312', password='stm312', measurement_codenames=['stm312_pirani', 'stm312_pc'])
db_logger.start()
"""

"""
while True:
    pirani = pressure_measurement.read_pressure()
    pc = pc_measurement.read_pressure()
    #datasocket.set_point_now('pirani', pirani)
    #datasocket.set_point_now('pc', pc)
    
    print(pirani)
    if pressure_measurement.trigged:
        print(pirani)
        #db_logger.enqueue_point_now('stm312_pirani', pirani)
        pressure_measurement.trigged = False
    
    print(pc)
    if pc_measurement.trigged:
        print(pc)
        #db_logger.enqueue_point_now('stm312_pc', pc)
        pc_measurement.trigged = False
    time.sleep(0.5)
"""

#Pullsocket = DateDataPullSocket('stm312 hpc pressure control', ['pressure', 'setpoint'])
#Pushsocket = DataPushSocket('stm312 hpc pressure control', action='store_last')


if __name__ == '__main__':
    print('program start')
    #Pullsocket.start()
    #Pushsocket.start()
    #socket.start()
    db_logger_stm312.start()
    #db_logger_ocs.start()
    time.sleep(1)

    pc = PcClass()
    #pc.add_socket_server(Pullsocket,Pushsocket)
    #pc.add_logger(db_logger_stm312)
    #pirani = PiraniClass()
    #pirani.add_logger(db_logger_stm312)

    baratron = Baratron()
    #baratron.deamon = True
    #baratron.start
    time.sleep(2)
    
    pc.start()
    pc.set_setpoint(2000)
    #pirani.start()
    time.sleep(2)
    #print(pirani.pressure)
    #for i in range(10):
    #    time.sleep(1)
    #    print(baratron.read_pressure())
    tui = CursesTui(pc)
    tui.deamon = True
    tui.start()
    
    print('Program End')
