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
        self.temperatures = {}
        self.setpoints = {}
        self.powers = {}
        self.quit = False
        self.ttl = 50
        for co in codenames:
            self.PIDs[co[:-5]+'pid'] = PID(pid_p=0.15, pid_i=0.0025, pid_d=0, p_max=100, p_min=-100)
            #self.setpoints[co[:-5]+'setpoint'] = None
            #self.temperatures[co[:-5]+'temperature'] = None
            #self.powers[co[:-5]+'power'] = 0.0
        self.temperatures = {'tabs_guard_temperature': None, 'tabs_floor_temperature': None, 'tabs_ceiling_temperature': None, 'tabs_cooling_temperature': None} 
        self.setpoints = {'tabs_guard_setpoint': None, 'tabs_floor_setpoint': None, 'tabs_ceiling_setpoint': None, 'tabs_cooling_setpoint': None} 
        self.powers = {'tabs_guard_power': None, 'tabs_floor_power': None, 'tabs_ceiling_power': None, 'tabs_cooling_power': None} 
        
    def update_temperatures(self,):
        info = socketinfo.INFO['tabs_temperatures']
        host_port = (info['host'], info['port'])
        command = 'json_wn'
        self.sock.sendto(command, host_port)
        data = json.loads(self.sock.recv(2048))
        #print(data)
        now = time.time()
        for key, value in data.items():
            co = str(key)
            if now - value[0] > 3*60 or value[1] == 'OLD_DATA': # this is 3min change to 5spowers
                # value to old
               self.temperatures[co] = None
            else:
                self.temperatures[co] = value[1]
        #print(self.temperatures)
        return self.temperatures
        
    def update_setpoints(self,):
        info = socketinfo.INFO['tabs_setpoints']
        host_port = (info['host'], info['port'])
        command = 'json_wn'
        self.sock.sendto(command, host_port)
        data = json.loads(self.sock.recv(2048))
        now = time.time()
        for key, value in data.items():
            try:
                if now - value[0] > 3*60: # this is 3min change to 5s
                    # value to old
                   self.setpoints[key] = None
                else:
                    self.setpoints[key] = value[1]
            except:
                pass
        #self.setpoints = {'tabs_guard_setpoint': 25.0, 'tabs_floor_setpoint': 25.0, 'tabs_ceiling_setpoint': 25.0, 'tabs_cooling_setpoint': 25.0}  
        return self.setpoints
    
    def update_powers(self,):
        for key, value in self.PIDs.items():
            co = str(key)
            setpoint = self.setpoints[co[:-3]+'setpoint']
            value.update_setpoint(setpoint)
            temperature = self.temperatures[co[:-3]+'temperature']
            self.powers[co[:-3]+'power'] = value.wanted_power(temperature)
        #print(self.powers)
        return self.powers
        
    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel == 0:
                return_val = self.powers['tabs_guard_power']
            elif channel == 1:
                return_val = self.powers['tabs_floor_power']
            elif channel == 2:
                return_val = self.powers['tabs_ceiling_power']
            elif channel == 3:
                return_val = self.powers['tabs_cooling_power']
        #print('return_val: ', return_val, '<-')
        return return_val
                
    def run(self):
        while not self.quit:
            time.sleep(1)
            self.update_temperatures()
            self.update_setpoints()
            self.update_powers()
            try:
                self.ttl = 50
                pass
            except:
                print('Run error in PidTemperatureControl')
    def stop(self,):
        self.quit = True
        
if __name__ == '__main__':
    codenames = ['tabs_guard_power',
                 'tabs_floor_power',
                 'tabs_ceiling_power',
                 #'tabs_cooling_power',
                 ]
    sockname = 'tabs_powers'
    PullSocket = DateDataPullSocket(sockname, codenames, timeouts=[60.0]*len(codenames), port = socketinfo.INFO[sockname]['port'])
    PullSocket.start()
    
    PTC = PidTemperatureControl(codenames)
    PTC.start()
    #time.sleep(5)
    
    chlist = {'tabs_guard_power': 0, 'tabs_floor_power': 1, 'tabs_ceiling_power': 2, 'tabs_cooling_power': 3}
    loggers = {}
    for key in codenames:
        loggers[key] = ValueLogger(PTC, comp_val = 1.9, maximumtime=60,
                                        comp_type = 'lin', channel = chlist[key])
        loggers[key].start()
    #livesocket = LiveSocket('tabs_temperature_logger', codenames, 2)
    #livesocket.start()

    
    #db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=codenames)
    #print('Hostname of db logger: ' + db_logger.host)
    #db_logger.start()
    
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
                    #db_logger.enqueue_point_now(name, v)
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