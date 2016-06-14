# -*- coding: utf-8 -*-
# !/usr/bin/env python
# pylint: disable=C0301,R0904, C0103
""" Pressure and temperature logger """

from __future__ import print_function

import sys
sys.path.insert(1, '/home/pi/PyExpLabSys')

import threading
import time
import logging
import socket
import json
from PyExpLabSys.common.loggers import ContinuousLogger
import credentials
import socketinfo
ContinuousLogger.host = credentials.dbhost
ContinuousLogger.database = credentials.dbname
from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.auxiliary.pid import PID
#from PyExpLabSys.drivers.dataq_comm import DataQ
#import PyExpLabSys.drivers.omegabus as omegabus
#import PyExpLabSys.drivers.omega_cni as omega_CNi32
#import PyExpLabSys.drivers.kampstrup as kampstrup

logging.basicConfig(filename="logger_mypid.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)


import SocketServer
SocketServer.UDPServer.allow_reuse_address = True



def Safety(SYSTEMS):
    case1 = False
    case2 = False
    case3 = False
    try:
        case1 = SYSTEMS['tabs_cooling_temperature_inlet'] < 9.0
    except:
        pass
    try:
        case2 = (SYSTEMS['tabs_guard_temperature_inlet'] > 40.0 or 
        SYSTEMS['tabs_floor_temperature_inlet'] > 40.0 or
        SYSTEMS['tabs_ceiling_temperature_inlet'] > 40.0 or
        SYSTEMS['tabs_cooling_temperature_inlet'] > 40.0)
    except:
        pass
    try:
        case3 = sum([SYSTEMS['tabs_guard_valve_cooling'],
                     SYSTEMS['tabs_floor_valve_cooling'],
                     SYSTEMS['tabs_ceiling_valve_cooling']]) < 0.5
    except:
        pass
    #try:
    #    case3 = SYSTEMS['tabs_cooling_temperature_inlet'] < SYSTEMS['tabs_cooling_temperature_setpoint']  - 2.0
    #except:
    #    pass
    if case1:
        if __name__ == '__main__':
            print("case 1")
        SYSTEMS['tabs_guard_pid_value'] = -1
        SYSTEMS['tabs_floor_pid_value'] = -1
        SYSTEMS['tabs_ceiling_pid_value'] = -1
        SYSTEMS['tabs_cooling_pid_value'] = 0
        
        SYSTEMS['tabs_guard_valve_heating'] = 1
        SYSTEMS['tabs_floor_valve_heating'] = 1
        SYSTEMS['tabs_ceiling_valve_heating'] = 1
        
        SYSTEMS['tabs_guard_valve_cooling'] = 1
        SYSTEMS['tabs_floor_valve_cooling'] = 1
        SYSTEMS['tabs_ceiling_valve_cooling'] = 1
        SYSTEMS['tabs_cooling_valve_cooling'] = 0
    elif case2:
        if __name__ == '__main__':
            print('Log: ', i, name, v)
        SYSTEMS['tabs_guard_valve_heating'] = 0
        SYSTEMS['tabs_floor_valve_heating'] = 0
        SYSTEMS['tabs_ceiling_valve_heating'] = 0
        
        SYSTEMS['tabs_guard_valve_cooling'] = 1
        SYSTEMS['tabs_floor_valve_cooling'] = 1
        SYSTEMS['tabs_ceiling_valve_cooling'] = 1
        SYSTEMS['tabs_cooling_valve_cooling'] = 0
    elif case3:
        if __name__ == '__main__':
            print("case 3")
        SYSTEMS['tabs_cooling_pid_value'] = 0
        SYSTEMS['tabs_cooling_valve_cooling'] = 0
    return SYSTEMS


class PidTemperatureControl(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        logging.info('PidTemperatureControl class started')
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(3)
        self.PIDs = {}
        #self.temperatures = {}
        #self.setpoints = {}
        #self.pidvalues = {}
        self.quit = False
        self.ttl = 50
        self.SYSTEMS = {'tabs_cooling_temperature_inlet': None}
        self.SYSTEMS = Safety(self.SYSTEMS)

        self.SYSTEMS['tabs_guard_pid_value'] = 0.0
        self.SYSTEMS['tabs_floor_pid_value'] = 0.0
        self.SYSTEMS['tabs_ceiling_pid_value'] = 0.0
        self.SYSTEMS['tabs_cooling_pid_value'] = 0.0
        
        self.PIDs = {}
        self.PIDs['tabs_guard_pid_value'] = PID(pid_p=0.05, pid_i=0.2/3600.0, pid_d=0, p_max=1, p_min=-1)
        self.PIDs['tabs_floor_pid_value'] = PID(pid_p=0.05, pid_i=0.2/3600.0, pid_d=0, p_max=1, p_min=-1)
        self.PIDs['tabs_ceiling_pid_value'] = PID(pid_p=0.05, pid_i=0.2/3600.0, pid_d=0, p_max=1, p_min=-1)
        self.PIDs['tabs_cooling_pid_value'] = PID(pid_p=0.05, pid_i=0.2/3600.0, pid_d=0, p_max=0, p_min=-0.4)
        
        self.PIDs['tabs_guard_pid_value'].int_err = self.PIDs['tabs_guard_pid_value'].p_min
        self.PIDs['tabs_floor_pid_value'].int_err = self.PIDs['tabs_floor_pid_value'].p_min
        self.PIDs['tabs_ceiling_pid_value'].int_err = self.PIDs['tabs_ceiling_pid_value'].p_min
        self.PIDs['tabs_cooling_pid_value'].int_err = self.PIDs['tabs_guard_pid_value'].p_max
            #self.setpoints[co[:-5]+'setpoint'] = None
            #self.temperatures[co[:-5]+'temperature'] = None
            #self.powers[co[:-5]+'power'] = 0.0
        #self.temperatures = {'tabs_guard_temperature': None, 'tabs_floor_temperature': None, 'tabs_ceiling_temperature': None, 'tabs_cooling_temperature': None} 
        #self.setpoints = {'tabs_guard_setpoint': None, 'tabs_floor_setpoint': None, 'tabs_ceiling_setpoint': None, 'tabs_cooling_setpoint': None} 
        #self.pidvalue = {'tabs_guard_pid': None, 'tabs_floor_pid': None, 'tabs_ceiling_pid': None, 'tabs_cooling_pid': None} 
        
    def update_temperatures(self,):
        try:
            info = socketinfo.INFO['tabs_temperatures']
            host_port = (info['host'], info['port'])
            command = 'json_wn'
            self.sock.sendto(command, host_port)
            data = json.loads(self.sock.recv(2*2048))
            #print(data)
            now = time.time()
            for key, value in data.items():
                try:
                    if abs(now - value[0]) > 3*60 or value[1] == 'OLD_DATA': # this is 3min change to 5s
                        # value to old
                       #self.pidvalues[co] = 0.0
                       self.SYSTEMS[key] = None
                    else:
                        self.SYSTEMS[key] = value[1]
                except:
                    self.SYSTEMS[key] = None
                    logging.warn('Cant calculate time difference')
            #print(self.temperatures)
        except socket.timeout:
            logging.warn('Socket timeout')
        return self.SYSTEMS
        
    def update_setpoints(self,):
        try:
            info = socketinfo.INFO['tabs_setpoints']
            host_port = (info['host'], info['port'])
            command = 'json_wn'
            self.sock.sendto(command, host_port)
            data = json.loads(self.sock.recv(2*2048))
            #print(data)
            now = time.time()
            for key, value in data.items():
                try:
                    if abs(now - value[0]) > 3*60 or value[1] == 'OLD_DATA': # this is 3min change to 5s
                        # value to old
                       #self.pidvalues[co] = 0.0
                       self.SYSTEMS[key] = None
                    else:
                        self.SYSTEMS[key] = value[1]
                except:
                    self.SYSTEMS[key] = None
                    logging.warn('Cant calculate time difference')
                #print(self.SYSTEMS[sy][me])
        except socket.timeout:
            logging.warn('Socket timeout')
        self.SYSTEMS = Safety(self.SYSTEMS)
        return self.SYSTEMS
    
    def update_pidvalues(self,):
        for key, value in self.PIDs.items():
            sy = key[:-len('pid_value')]
            #co = str(key)
            setpoint = self.SYSTEMS[sy+'temperature_setpoint']
            if setpoint == None:
                pass
            else:
                self.PIDs[key].update_setpoint(setpoint)
            if sy == 'tabs_guard_':
                temperature = self.SYSTEMS[sy + 'temperature_control']
            else:
                temperature = self.SYSTEMS[sy + 'temperature_inlet']
            #print(temperature)
            if temperature == None:
                pass
            else:
                self.SYSTEMS[sy+'pid_value'] = self.PIDs[key].wanted_power(temperature)
                if self.SYSTEMS[sy+'pid_value'] > 0:
                    self.SYSTEMS[sy+'valve_heating'] = abs(self.SYSTEMS[sy+'pid_value'])
                    self.SYSTEMS[sy+'valve_cooling'] = abs(0.05)
                elif self.SYSTEMS[sy+'pid_value'] < 0:
                    self.SYSTEMS[sy+'valve_heating'] = abs(0.0)
                    self.SYSTEMS[sy+'valve_cooling'] = max(0.05, abs(self.SYSTEMS[sy+'pid_value']) )
                else:
                    self.SYSTEMS[sy+'valve_heating'] = 0
                    self.SYSTEMS[sy+'valve_cooling'] = max(0.1, abs(self.SYSTEMS[sy+'pid_value']) )
                if sy+'pid_value' == 'tabs_cooling_pid_values':
                    self.SYSTEMS[sy+'valve_cooling'] = abs(self.SYSTEMS[sy+'pid_value'])
                self.SYSTEMS['tabs_cooling_valve_cooling'] = abs(self.SYSTEMS['tabs_cooling_pid_value'])
        self.SYSTEMS = Safety(self.SYSTEMS)
            #print(value['pid_values'])
        #print(self.powers)
        return self.SYSTEMS
        
    def value(self, channel):
        """ Read the pressure """
        chlist = {'tabs_guard_pid_value': 0,
                  'tabs_floor_pid_value': 1,
                  'tabs_ceiling_pid_value': 2,
                  'tabs_cooling_pid_value': 3,
                  
                  'tabs_guard_valve_heating': 4,
                  'tabs_floor_valve_heating': 5,
                  'tabs_ceiling_valve_heating': 6,
                  
                  'tabs_guard_valve_cooling': 7,
                  'tabs_floor_valve_cooling': 8,
                  'tabs_ceiling_valve_cooling': 9,
                  'tabs_cooling_valve_cooling': 10}
        self.ttl = self.ttl - 1
        #print('ttl: ', self.ttl, channel)
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            for key, value in chlist.items():
                if channel == value:
                    return_val = self.SYSTEMS[key]
                    break
        #print('return_val: ' , return_val)
        return return_val
                
    def run(self):
        while not self.quit:
            time.sleep(0.5)
            self.update_temperatures()
            self.update_setpoints()
            self.update_pidvalues()
            try:
                self.ttl = 50
                pass
            except:
                #print('Run error in PidTemperatureControl')
                pass
    def stop(self,):
        self.quit = True

class MainPID(threading.Thread):
    """ pid controller """
    def __init__(self,):
        logging.info('MainPID class started')
        threading.Thread.__init__(self)
        #from datalogger import TemperatureReader
        self.quit = False
        self.codenames = ['tabs_guard_pid_value',
                 'tabs_floor_pid_value',
                 'tabs_ceiling_pid_value',
                 'tabs_cooling_pid_value',
                 
                 'tabs_guard_valve_heating',
                 'tabs_floor_valve_heating',
                 'tabs_ceiling_valve_heating',
                 
                 'tabs_guard_valve_cooling',
                 'tabs_floor_valve_cooling',
                 'tabs_ceiling_valve_cooling',
                 'tabs_cooling_valve_cooling',
                 ]
        sockname = 'tabs_pids'
        self.PullSocket = DateDataPullSocket(sockname, self.codenames, timeouts=[60.0]*len(self.codenames), port = socketinfo.INFO[sockname]['port'])
        self.PullSocket.start()
    
        self.PTC = PidTemperatureControl(self.codenames)
        self.PTC.daemon = True
        self.PTC.start()
        #time.sleep(5)
    
        chlist = {'tabs_guard_pid_value': 0,
                  'tabs_floor_pid_value': 1,
                  'tabs_ceiling_pid_value': 2,
                  'tabs_cooling_pid_value': 3,
                  
                  'tabs_guard_valve_heating': 4,
                  'tabs_floor_valve_heating': 5,
                  'tabs_ceiling_valve_heating': 6,
                  
                  'tabs_guard_valve_cooling': 7,
                  'tabs_floor_valve_cooling': 8,
                  'tabs_ceiling_valve_cooling': 9,
                  'tabs_cooling_valve_cooling': 10}
        self.loggers = {}
        for key in self.codenames:
            self.loggers[key] = ValueLogger(self.PTC, comp_val = 0.10, maximumtime=60,
                                        comp_type = 'lin', channel = chlist[key])
            self.loggers[key].start()
        #livesocket = LiveSocket('tabs_temperature_logger', codenames, 2)
        #livesocket.start()

    
        self.db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=self.codenames)
        self.db_logger.start()

    def run(self,):
        i = 0
        while not self.quit and self.PTC.isAlive():
            try:
                #print(i)
                time.sleep(1)
                for name in self.codenames:
                    v = self.loggers[name].read_value()
                    #print('Status: ', name , v)
                    #livesocket.set_point_now(name, v)
                    self.PullSocket.set_point_now(name, v)
                    if self.loggers[name].read_trigged():
                        if __name__ == '__main__':
                            print('Log: ', i, name, v)
                        #print(i, name, v)
                        self.db_logger.enqueue_point_now(name, v)
                        self.loggers[name].clear_trigged()
            except (KeyboardInterrupt, SystemExit):
                self.quit = True
                pass
                #self.PTC.stop()
                #report error and proceed
            i += 1
        self.stop()

    def stop(self):
        self.quit = True
        self.PTC.stop()
        self.PullSocket.stop()
        self.db_logger.stop()
        for key in self.codenames:
            self.loggers[key].status['quit'] = True

        
if __name__ == '__main__':
    MPID = MainPID()
    time.sleep(3)
    MPID.start()
    
    while MPID.isAlive():
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            MPID.quit = True
    #print('END')

