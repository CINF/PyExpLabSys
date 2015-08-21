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

class FloatToDigital(object):
    def __init__(self, totalcycles=100):
        self.cycle = 0
        self.totalcycles = totalcycles
        self.dutycycles = 0.0
    
    def update(dutycycles):
        if dutycycles < 0 or dutycycles > 1:
            print('dutycycles is outside allowed area, should be between 0-1')
        if (self.cycle/self.totalcycles) < self.dutycycles:
            result = True
        else:
            result = False
        self.cycle += 1
        self.cycle %= self.totalcycles
        return result


class ValveControl(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        threading.Thread.__init__(self)
        self.quit = False
        self.codenames = codenames
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
        port = '/dev/serial/by-id/usb-0683_1490-if00'
        self.DATAQ = DataQ(port=port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.pidvalues = {'tabs_guard_pid': 0.0, 'tabs_floor_pid': 0.0, 'tabs_ceiling_pid': 0.0, 'tabs_cooling_pid': 0.0}
        #self.heater = {'tabs_guard_heater': None, 'tabs_floor_heater': None, 'tabs_ceiling_heater': None, 'tabs_cooling_heater': None}
        self.FloatToDigital = {}
        for sy in self.SYSTEMS.keys():
            for va in ['valve_cooling', 'valve_heating']:
                self.FloatToDigital[sy+'_'+va] = FloatToDigital(totalcycles=100)
        
    def update_pidvalues(self,):
        info = socketinfo.INFO['tabs_pids']
        host_port = (info['host'], info['port'])
        command = 'json_wn'
        self.sock.sendto(command, host_port)
        data = json.loads(self.sock.recv(2048))
        #print('New Power settings: ', data)
        now = time.time()
        for key, value in data.items():
            _key = str(key).rsplit('_')
            sy = _key[0]+'_' + _key[1]
            me = _key[2]+'_' + _key[3]
            try:
                if now - value[0] > 3*60 or value[1] == 'OLD_DATA': # this is 3min change to 5s
                    # value to old
                   #self.pidvalues[co] = 0.0
                   self.SYSTEMS[sy][me] = None
                else:
                    self.SYSTEMS[sy][me] = value[1]
            except:
                self.SYSTEMS[sy][me] = None
                #self.powers[co] = 0.0
        #print('Valve powers: ', self.powers)
        return self.SYSTEMS
        
    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
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
        #print('return_val: ', return_val, '<-')
        return return_val
    
    def update_DO(self,):
        self.ttl = self.ttl - 1
        OnOffSignal = {}
        for key, value in self.FloatToDigital.keys():
            sy = key[0]+'_' + key[1]
            me = key[2]+'_' + key[3]
            OnOffSignal[key] = value.update(self.SYSTEMS[sy][me])
        #print('Valve settings: ' , v)
        try:
            self.DATAQ.setOutputs(ch0=OnOffSignal['tabs_guard_valve_heating'],
                                  ch1=OnOffSignal['tabs_floor_valve_heating'],
                                  ch2=OnOffSignal['tabs_ceiling_valve_heating'],
                                  ch3=OnOffSignal['tabs_cooling_valve_heating'])
            self.ttl = 50
        except:
            print('Cant set digital out')
            
    def run(self):
        while not self.quit:
            time.sleep(1)
            self.update_pidvalues()
            try:
                self.update_DO()
                #self.ttl = 50
                pass
            except:
                print('Run error in PidTemperatureControl')
    def stop(self,):
        self.quit = True

class MainDGIO(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        threading.Thread.__init__(self)
        #from digitalinot import ValveControl
        self.quit = False
        self.codenames = ['tabs_guard_valve_heating',
                     'tabs_floor_valve_heating',
                     'tabs_ceiling_valve_heating',
                     'tabs_cooling_valve_heating',
                     ]
        sockname = 'tabs_valve'
        #codenames = socketinfo.INFO[sockname]['codenames']
        self.PullSocket = DateDataPullSocket(sockname, self.codenames, timeouts=[60.0]*len(self.codenames), port = socketinfo.INFO[sockname]['port'])
        self.PullSocket.start()
        self.VC = ValveControl(self.codenames)
        self.VC.start()
        chlist = {'tabs_guard_valve_heating': 0, 'tabs_floor_valve_heating': 1, 'tabs_ceiling_valve_heating': 2, 'tabs_cooling_valve_heating': 3}
        self.loggers = {}
        for key in self.codenames:
            self.loggers[key] = ValueLogger(self.VC, comp_val = 1.9, maximumtime=60, comp_type = 'lin', channel = chlist[key])
            self.loggers[key].start()
    def run(self,):
        i = 0
        while not self.quit:
            try:
                #print(i)
                time.sleep(2)
                for name in self.codenames:
                    v = self.loggers[name].read_value()
                    #print('Status: ', name , v)
                    #livesocket.set_point_now(name, v)
                    self.PullSocket.set_point_now(name, v)
                    if self.loggers[name].read_trigged():
                        #print('Log: ', name, v)
                        #db_logger.enqueue_point_now(name, v)
                        self.loggers[name].clear_trigged()
            except (KeyboardInterrupt, SystemExit):
                self.VC.stop()
                #report error and proceed
            i += 1
    def stop(self):
        self.quit = True
        self.PullSocket.stop()
        for key in self.codenames:
            self.loggers[key].status['quit'] = True

if __name__ == '__main__':
    DGIO = MainDGIO()
    DGIO.start()
    
    while DGIO.isAlive():
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            DGIO.stop()
    print('END')
