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
from PyExpLabSys.drivers.dataq_comm import DataQ
#import PyExpLabSys.drivers.omegabus as omegabus
#import PyExpLabSys.drivers.omega_cni as omega_CNi32
#import PyExpLabSys.drivers.kampstrup as kampstrup

#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)

import SocketServer
SocketServer.UDPServer.allow_reuse_address = True






class PidTemperatureControl(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.PIDs = {}
        #self.temperatures = {}
        #self.setpoints = {}
        #self.pidvalues = {}
        self.quit = False
        self.ttl = 50
        self.SYSTEMS = {}
        for sy in ['tabs_guard', 'tabs_floor', 'tabs_ceiling', 'tabs_cooling', 'tabs_ice']:
            self.SYSTEMS[sy] = {'temperature_inlet': None, # float in C
                                'temperature_outlet': None, # float in C
                                'temperature_setpoint': None, # float in C
                                'valve_cooling': None, # float 0-1
                                'valve_heating': None, # float 0-1
                                'pid_value': None, # float -1-1
                                'water_flow': None} # float in l/min
        for sy, value in self.SYSTEMS.items():
            value['pid_value'] = 0.0
        self.PIDs = {}
        for sy in self.SYSTEMS.keys():
            self.PIDs[sy+'_pid_value'] = PID(pid_p=0.015, pid_i=0.00025, pid_d=0, p_max=1, p_min=-1)
            #self.setpoints[co[:-5]+'setpoint'] = None
            #self.temperatures[co[:-5]+'temperature'] = None
            #self.powers[co[:-5]+'power'] = 0.0
        #self.temperatures = {'tabs_guard_temperature': None, 'tabs_floor_temperature': None, 'tabs_ceiling_temperature': None, 'tabs_cooling_temperature': None} 
        #self.setpoints = {'tabs_guard_setpoint': None, 'tabs_floor_setpoint': None, 'tabs_ceiling_setpoint': None, 'tabs_cooling_setpoint': None} 
        #self.pidvalue = {'tabs_guard_pid': None, 'tabs_floor_pid': None, 'tabs_ceiling_pid': None, 'tabs_cooling_pid': None} 
        
    def update_temperatures(self,):
        info = socketinfo.INFO['tabs_temperatures']
        host_port = (info['host'], info['port'])
        command = 'json_wn'
        self.sock.sendto(command, host_port)
        data = json.loads(self.sock.recv(2048))
        #print(data)
        now = time.time()
        for key, value in data.items():
            _key = str(key).rsplit('_')
            sy = _key[0]+'_' + _key[1]
            me = _key[2]+'_' + _key[3]
            try:
                if abs(now - value[0]) > 3*60 or value[1] == 'OLD_DATA': # this is 3min change to 5s
                    # value to old
                   #self.pidvalues[co] = 0.0
                   self.SYSTEMS[sy][me] = None
                else:
                    self.SYSTEMS[sy][me] = value[1]
            except:
                self.SYSTEMS[sy][me] = None
        #print(self.temperatures)
        return self.SYSTEMS
        
    def update_setpoints(self,):
        info = socketinfo.INFO['tabs_setpoints']
        host_port = (info['host'], info['port'])
        command = 'json_wn'
        self.sock.sendto(command, host_port)
        data = json.loads(self.sock.recv(2048))
        #print(data)
        now = time.time()
        for key, value in data.items():
            _key = str(key).rsplit('_')
            sy = _key[0]+'_' + _key[1]
            me = _key[2]+'_' + _key[3]
            try:
                if abs(now - value[0]) > 3*60 or value[1] == 'OLD_DATA': # this is 3min change to 5s
                    # value to old
                   #self.pidvalues[co] = 0.0
                   self.SYSTEMS[sy][me] = None
                else:
                    self.SYSTEMS[sy][me] = value[1]
            except:
                self.SYSTEMS[sy][me] = None
            #print(self.SYSTEMS[sy][me])
        return self.SYSTEMS
    
    def update_pidvalues(self,):
        for sy, value in self.SYSTEMS.items():
            #co = str(key)
            setpoint = value['temperature_setpoint']
            if setpoint == None:
                pass
            else:
                self.PIDs[sy+'_pid_value'].update_setpoint(setpoint)
            temperature = value['temperature_inlet']
            #print(temperature)
            if temperature == None:
                pass
            else:
                value['pid_value'] = self.PIDs[sy+'_pid_value'].wanted_power(temperature)
            #print(value['pid_values'])
        #print(self.powers)
        return self.SYSTEMS
        
    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        #print('ttl: ', self.ttl, channel)
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            me = 'pid_value'
            if channel == 0:
                sy = 'tabs_guard'
                return_val = self.SYSTEMS[sy][me]
            elif channel == 1:
                sy = 'tabs_floor'
                return_val = self.SYSTEMS[sy][me]
            elif channel == 2:
                sy = 'tabs_ceiling'
                return_val = self.SYSTEMS[sy][me]
            elif channel == 3:
                sy = 'tabs_cooling'
                return_val = self.SYSTEMS[sy][me]
        #print('return_val: ' , return_val)
        return return_val
                
    def run(self):
        while not self.quit:
            time.sleep(1)
            self.update_temperatures()
            self.update_setpoints()
            self.update_pidvalues()
            try:
                self.ttl = 50
                pass
            except:
                print('Run error in PidTemperatureControl')
    def stop(self,):
        self.quit = True
        
if __name__ == '__main__':
    codenames = ['tabs_guard_pid_value',
                 'tabs_floor_pid_value',
                 'tabs_ceiling_pid_value',
                 'tabs_cooling_pid_value',
                 ]
    sockname = 'tabs_pids'
    PullSocket = DateDataPullSocket(sockname, codenames, timeouts=[60.0]*len(codenames), port = socketinfo.INFO[sockname]['port'])
    PullSocket.start()
    
    PTC = PidTemperatureControl(codenames)
    PTC.start()
    #time.sleep(5)
    
    chlist = {'tabs_guard_pid_value': 0, 'tabs_floor_pid_value': 1, 'tabs_ceiling_pid_value': 2, 'tabs_cooling_pid_value': 3}
    loggers = {}
    for key in codenames:
        loggers[key] = ValueLogger(PTC, comp_val = 0.10, maximumtime=60,
                                        comp_type = 'lin', channel = chlist[key])
        loggers[key].start()
    #livesocket = LiveSocket('tabs_temperature_logger', codenames, 2)
    #livesocket.start()

    
    db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=codenames)
    print('Hostname of db logger: ' + db_logger.host)
    db_logger.start()
    
    i = 0
    while PTC.isAlive():
        print(i)
        try:
            #print(i)
            time.sleep(2)
            for name in codenames:
                v = loggers[name].read_value()
                print('Status: ', name , v)
                #livesocket.set_point_now(name, v)
                PullSocket.set_point_now(name, v)
                if loggers[name].read_trigged():
                    print('Log: ', name, v)
                    db_logger.enqueue_point_now(name, v)
                    loggers[name].clear_trigged()
        except (KeyboardInterrupt, SystemExit):
            PTC.stop()
            #report error and proceed
        i += 1
    PullSocket.stop()
    for key in codenames:
        loggers[key].status['quit'] = True
    print(i)
    print('END')
