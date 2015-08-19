# -*- coding: utf-8 -*-
# !/usr/bin/env python
# pylint: disable=C0301,R0904, C0103
""" Pressure and temperature logger """

from __future__ import print_function

import sys
sys.path.insert(1, '/home/pi/PyExpLabSys')
#sys.path.insert(2, '../..')

import threading
import time
import logging
import socket
import json
#from PyExpLabSys.common.loggers import ContinuousLogger
import credentials
import socketinfo
#ContinuousLogger.host = credentials.dbhost
#ContinuousLogger.database = credentials.dbname
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.drivers.dataq_comm import DataQ
from PyExpLabSys.common.value_logger import ValueLogger
#from PyExpLabSys.auxiliary.pid import PID
#import PyExpLabSys.drivers.omegabus as omegabus
#import PyExpLabSys.drivers.omega_cni as omega_CNi32
#import PyExpLabSys.drivers.kampstrup as kampstrup

#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)


class ValveControl(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        threading.Thread.__init__(self)
        self.quit = False
        self.codenames = codenames
        self.ttl = 50
        port = '/dev/serial/by-id/usb-0683_1490-if00'
        self.DATAQ = DataQ(port=port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.powers = {'tabs_guard_power': 0.0, 'tabs_floor_power': 0.0, 'tabs_ceiling_power': 0.0, 'tabs_cooling_power': 0.0}
        #self.heater = {'tabs_guard_heater': None, 'tabs_floor_heater': None, 'tabs_ceiling_heater': None, 'tabs_cooling_heater': None}
        
    def update_powers(self,):
        info = socketinfo.INFO['tabs_powers']
        host_port = (info['host'], info['port'])
        command = 'json_wn'
        self.sock.sendto(command, host_port)
        data = json.loads(self.sock.recv(2048))
        #print('New Power settings: ', data)
        now = time.time()
        for key, value in data.items():
            try:
                co = str(key)
                if now - value[0] > 3*60 or value[1] == 'OLD_DATA': # this is 3min change to 5s
                    # value to old
                   self.powers[co] = 0.0
                else:
                    self.powers[co] = value[1]
            except:
                pass
                #self.powers[co] = 0.0
        #print('Valve powers: ', self.powers)
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
    
    def update_DO(self,):
        self.ttl = self.ttl - 1
        v = []
        for i in range(4):
            v += [self.value(i) < -50]
        #print('Valve settings: ' , v)
        try:
            self.DATAQ.setOutputs(ch0=v[0],
                                  ch1=v[1],
                                  ch2=v[2],
                                  ch3=v[3])
            self.ttl = 50
        except:
            print('Cant set digital out')
            
    def run(self):
        while not self.quit:
            time.sleep(1)
            self.update_powers()
            try:
                self.update_DO()
                #self.ttl = 50
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
    sockname = 'tabs_valve'
    PullSocket = DateDataPullSocket(sockname, codenames, timeouts=[60.0]*len(codenames), port = socketinfo.INFO[sockname]['port'])
    PullSocket.start()
    VC = ValveControl(codenames)
    VC.start()
    chlist = {'tabs_guard_power': 0, 'tabs_floor_power': 1, 'tabs_ceiling_power': 2, 'tabs_cooling_power': 3}
    loggers = {}
    for key in codenames:
        loggers[key] = ValueLogger(VC, comp_val = 1.9, maximumtime=60, comp_type = 'lin', channel = chlist[key])
        loggers[key].start()
    i = 0
    while VC.isAlive():
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
            VC.stop()
            #report error and proceed
        i += 1
    PullSocket.stop()
    for key in codenames:
        loggers[key].status['quit'] = True
    print(i)
    print('End')
