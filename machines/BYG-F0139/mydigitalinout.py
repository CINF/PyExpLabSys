# -*- coding: utf-8 -*-
# !/usr/bin/env python
# pylint: disable=C0301,R0904, C0103
""" Pressure and temperature logger """

from __future__ import print_function, division

import sys
sys.path.insert(1, '/home/pi/PyExpLabSys')
#sys.path.insert(2, '../..')

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
from PyExpLabSys.drivers.dataq_comm import DataQ
from PyExpLabSys.drivers.omega_D6720 import OmegaD6720
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
    
    def update(self, dutycycles):
        #print(dutycycles)
        self.dutycycles = dutycycles
        if self.dutycycles < 0 or self.dutycycles > 1:
            print('dutycycles is outside allowed area, should be between 0-1')
        #print(self.cycle/self.totalcycles, self.dutycycles)
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
        for sy in ['tabs_guard', 'tabs_floor', 'tabs_ceiling', 'tabs_cooling']: #, 'tabs_ice'
            self.SYSTEMS[sy] = {'temperature_inlet': None, # float in C
                                'temperature_outlet': None, # float in C
                                'temperature_setpoint': None, # float in C
                                'valve_cooling': None, # float 0-1
                                'valve_heating': None, # float 0-1
                                'pid_value': None, # float -1-1
                                'water_flow': None} # float in l/min
        port = '/dev/serial/by-id/usb-0683_1490-if00'
        self.DATAQ = DataQ(port=port)
        port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTYIWN2Q-if00-port0'
        self.omega = OmegaD6720(1, port=port)
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
        #print('SOCK: ', data)
        for key, value in data.items():
            _key = str(key).rsplit('_')
            sy = _key[0]+'_' + _key[1]
            me = _key[2]+'_' + _key[3]
            #print('SOCK: ', key, value)
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
            #print('sock: rturn', self.SYSTEMS[sy][me])
        return self.SYSTEMS
        
    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            me = 'valve_heating'
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
            me = 'valve_cooling'
            if channel == 4:
                sy = 'tabs_guard'
                return_val = self.SYSTEMS[sy][me]
            elif channel == 5:
                sy = 'tabs_floor'
                return_val = self.SYSTEMS[sy][me]
            elif channel == 6:
                sy = 'tabs_ceiling'
                return_val = self.SYSTEMS[sy][me]
            elif channel == 7:
                sy = 'tabs_cooling'
                return_val = self.SYSTEMS[sy][me]
        #print('return_val: ', return_val, '<-')
        return return_val
    
    def update_DO(self,):
        self.ttl = self.ttl - 1
        keytochannel = {'tabs_guard_valve_heating': 0,
                        'tabs_floor_valve_heating': 1,
                        'tabs_ceiling_valve_heating': 2,
                        'tabs_cooling_valve_heating': 3,
                        'tabs_ice_valve_heating': 4,
                        'tabs_guard_valve_cooling': 5,
                        'tabs_floor_valve_cooling': 6,
                        'tabs_ceiling_valve_cooling': 7,
                        'tabs_cooling_valve_cooling': 8,
                        'tabs_ice_valve_cooling': 9,}
        OnOffSignal = {}
        if self.SYSTEMS['tabs_cooling']['temperature_inlet'] < 5.0:
            self.SYSTEMS['tabs_guard']['pid_value'] = -1.0
            self.SYSTEMS['tabs_floor']['pid_value'] = -1.0
            self.SYSTEMS['tabs_ceiling']['pid_value'] = -1.0
        for key, value in self.FloatToDigital.items(): 
            try:
                _key = str(key).rsplit('_')
                sy = _key[0]+'_' + _key[1]
                me = _key[2]+'_' + _key[3]
                #print('SYS', self.SYSTEMS[sy]['pid_value'])
                val = self.SYSTEMS[sy]['pid_value']
                if me == 'valve_heating' and val > 0:
                    self.SYSTEMS[sy][me] = abs(val)
                elif me == 'valve_heating' and val < 0:
                    self.SYSTEMS[sy][me] = 0.0
                elif me == 'valve_cooling' and val > 0:
                    self.SYSTEMS[sy][me] = 0.0
                elif me == 'valve_cooling' and val < 0:
                    self.SYSTEMS[sy][me] = abs(val)
                else:
                    self.SYSTEMS[sy][me] = 0
            except:
                print('error')
        try:
            for key, value in self.FloatToDigital.items():
                OnOffSignal[key] = int(value.update(self.SYSTEMS[sy][me]))
                if me == 'valve_heating':
                    #print(keytochannel[key], int(OnOffSignal[key]))
                    self.omega.write_channel(ch=keytochannel[key], value=int(OnOffSignal[key]))
                    #write_channel(self,ch=0, value=0)
            self.DATAQ.setOutputs(ch0=OnOffSignal['tabs_guard_valve_cooling'],
                                  ch1=OnOffSignal['tabs_floor_valve_cooling'],
                                  ch2=OnOffSignal['tabs_ceiling_valve_cooling'],
                                  ch3=OnOffSignal['tabs_cooling_valve_cooling'])

            self.ttl = 50
        except:
            print('error')
 
            
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
        #self.DATAQ.close()
        self.omega.all_off()
        self.omega.close()

class MainDGIO(threading.Thread):
    """ Temperature reader """
    def __init__(self):
        threading.Thread.__init__(self)
        #from digitalinot import ValveControl
        self.quit = False
        self.codenames = ['tabs_guard_valve_heating',
                     'tabs_floor_valve_heating',
                     'tabs_ceiling_valve_heating',
                     'tabs_cooling_valve_heating',
                     'tabs_guard_valve_cooling',
                     'tabs_floor_valve_cooling',
                     'tabs_ceiling_valve_cooling',
                     'tabs_cooling_valve_cooling',
                     ]
        sockname = 'tabs_valve'
        #codenames = socketinfo.INFO[sockname]['codenames']
        self.PullSocket = DateDataPullSocket(sockname, self.codenames, timeouts=[60.0]*len(self.codenames), port = socketinfo.INFO[sockname]['port'])
        self.PullSocket.start()
        self.VC = ValveControl(self.codenames)
        self.VC.start()
        chlist = {'tabs_guard_valve_heating': 0,
                  'tabs_floor_valve_heating': 1,
                  'tabs_ceiling_valve_heating': 2,
                  'tabs_cooling_valve_heating': 3,
                  'tabs_guard_valve_cooling': 4,
                  'tabs_floor_valve_cooling': 5,
                  'tabs_ceiling_valve_cooling': 6,
                  'tabs_cooling_valve_cooling': 7}
        self.loggers = {}
        for key in self.codenames:
            self.loggers[key] = ValueLogger(self.VC, comp_val = 0.05, maximumtime=60, comp_type = 'lin', channel = chlist[key])
            self.loggers[key].start()
        self.db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=self.codenames)
        self.db_logger.start()
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
                        print('Log: ', name, v)
                        self.db_logger.enqueue_point_now(name, v)
                        self.loggers[name].clear_trigged()
            except (KeyboardInterrupt, SystemExit):
                pass
                #self.VC.stop()
                #report error and proceed
            i += 1
    def stop(self):
        self.quit = True
        self.VC.stop()
        self.PullSocket.stop()
        self.db_logger.stop()
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
