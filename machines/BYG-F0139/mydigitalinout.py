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
from PyExpLabSys.drivers.omega_D6000 import OmegaD6720
from PyExpLabSys.drivers.omega_D6000 import OmegaD6500
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.drivers.cpx400dp import CPX400DPDriver
#from PyExpLabSys.auxiliary.pid import PID
#import PyExpLabSys.drivers.omegabus as omegabus
#import PyExpLabSys.drivers.omega_cni as omega_CNi32
#import PyExpLabSys.drivers.kampstrup as kampstrup

logging.basicConfig(filename="logger_mydgitalinout.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)


import random
class FloatToDigital(object):
    def __init__(self, totalcycles=100):
        self.cycle = 0
        self.totalcycles = totalcycles
        self.dutycycles = 0.0
    
    def update(self, dutycycles):
        #print(dutycycles)
        self.dutycycles = dutycycles
        if self.dutycycles < 0 or self.dutycycles > 1:
            if __name__ == '__main__':
                print('dutycycles is outside allowed area, should be between 0-1')
        #print(self.cycle/self.totalcycles, self.dutycycles)
        if (float(self.cycle)/float(self.totalcycles)) < self.dutycycles:
        #if (random.random()) < self.dutycycles:
            result = True
        else:
            result = False
        self.cycle += 1
        self.cycle %= self.totalcycles
        return result


class ValveControl(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        logging.info('ValveControl class started')
        threading.Thread.__init__(self)
        self.quit = False
        self.codenames = codenames
        self.ttl = 50
        self.SYSTEMS = {}
        for co in self.codenames:
            self.SYSTEMS[co] = None
        port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTYIWN2Q-if00-port0'
        self.omegaDO = OmegaD6720(1, port=port)
        self.omegaAO = {}
        self.omegaAO['tabs_guard_valve_cooling'] = OmegaD6500(2, port=port, activechannel=1)
        self.omegaAO['tabs_floor_valve_cooling'] = OmegaD6500(2, port=port, activechannel=2)
        self.omegaAO['tabs_ceiling_valve_cooling'] = OmegaD6500(3, port=port, activechannel=1)
        self.omegaAO['tabs_cooling_valve_cooling'] = OmegaD6500(3, port=port, activechannel=2)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.pidvalues = {'tabs_guard_pid': 0.0, 'tabs_floor_pid': 0.0, 'tabs_ceiling_pid': 0.0, 'tabs_cooling_pid': 0.0}
        #self.heater = {'tabs_guard_heater': None, 'tabs_floor_heater': None, 'tabs_ceiling_heater': None, 'tabs_cooling_heater': None}
        self.FloatToDigital = {}
        for key in ['tabs_guard_valve_heating',
                        'tabs_floor_valve_heating',
                        'tabs_ceiling_valve_heating']:
            self.FloatToDigital[key] = FloatToDigital(totalcycles=100)
        
    def update_pidvalues(self,):
        try:
            info = socketinfo.INFO['tabs_pids']
            host_port = (info['host'], info['port'])
            command = 'json_wn'
            self.sock.sendto(command, host_port)
            data = json.loads(self.sock.recv(2048))
            now = time.time()
            #print(data)
            for key, value in data.items():
                try:
                    if abs(now - value[0]) > 3*60 or value[1] == 'OLD_DATA': # this is 3min change to 5s
                       #self.SYSTEMS[sy][me] = None
                       pass
                    else:
                        self.SYSTEMS[key] = value[1]
                except:
                    logging.warn('except: cant calculate time difference')
                    pass
                    #self.SYSTEMS[sy][me] = None
        except socket.timeout:
            pass
        return self.SYSTEMS
    def update_temperatures(self,):
        """ Read the temperature from a external socket server"""
        try:
            info = socketinfo.INFO['tabs_temperatures']
            host_port = (info['host'], info['port'])
            command = 'json_wn'
            self.sock.sendto(command, host_port)
            data = json.loads(self.sock.recv(2048))
            now = time.time()
            #print(data)
            for key, value in data.items():
                try:
                    if abs(now - value[0]) > 3*60 or value[1] == 'OLD_DATA': # this is 3min change to 5s
                       #self.SYSTEMS[key] = None
                       pass
                    else:
                        self.SYSTEMS[key] = value[1]
                except:
                    #self.SYSTEMS[key] = None
                    logging.warn('except: cant calculate time difference')
                    pass
        except socket.timeout:
            pass
        return self.SYSTEMS
        
    def value(self, channel):
        """ Read the pressure """
        #self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            me = 'valve_heating'
            if channel == 0:
                sy = 'tabs_guard'
                return_val = self.SYSTEMS[sy+'_'+me]
            elif channel == 1:
                sy = 'tabs_floor'
                return_val = self.SYSTEMS[sy+'_'+me]
            elif channel == 2:
                sy = 'tabs_ceiling'
                return_val = self.SYSTEMS[sy+'_'+me]
            elif channel == 3:
                sy = 'tabs_cooling'
                return_val = self.SYSTEMS[sy+'_'+me]
            me = 'valve_cooling'
            if channel == 4:
                sy = 'tabs_guard'
                return_val = self.SYSTEMS[sy+'_'+me]
            elif channel == 5:
                sy = 'tabs_floor'
                return_val = self.SYSTEMS[sy+'_'+me]
            elif channel == 6:
                sy = 'tabs_ceiling'
                return_val = self.SYSTEMS[sy+'_'+me]
            elif channel == 7:
                sy = 'tabs_cooling'
                return_val = self.SYSTEMS[sy+'_'+me]
        #print('return_val: ', return_val, '<-')
        return return_val
    
    def update_DO(self,):
        #print('update_DO')
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
        
        if self.SYSTEMS['tabs_cooling_temperature_inlet'] < 10.0 and self.SYSTEMS['tabs_cooling_temperature_inlet'] != None:
            #print('Safety in progress')
            self.SYSTEMS['tabs_guard_valve_cooling'] = 1.0
            self.SYSTEMS['tabs_floor_valve_cooling'] = 1.0
            self.SYSTEMS['tabs_ceiling_valve_cooling'] = 1.0
            self.SYSTEMS['tabs_cooling_valve_cooling'] = -1.0
        OnOffSignal = {}
        for key, value in self.FloatToDigital.items():
            OnOffSignal[key] = value.update(self.SYSTEMS[key])
        try:
            for key, value in self.FloatToDigital.items():
                #_key = key.rsplit('_')
                #sy = _key[0]+'_' + _key[1]
                #me = _key[2]+'_' + _key[3]
                if 'valve_heating' in key:
                    #print(keytochannel[key], int(OnOffSignal[key]))
                    self.omegaDO.write_channel(ch=keytochannel[key], value=int(OnOffSignal[key]))

            self.ttl = 50
        except:
            logging.warn('except: cant write channels')
            
        try:
            for key in self.omegaAO.keys():
                v = 10.*self.SYSTEMS[key]
                #print(key, v)
                self.omegaAO[key].set_value(v)
                self.ttl = 50
                #print(key, v)
        except:
            logging.warn('except: cant set values')

    def run(self):
        while not self.quit:
            #print('------------')
            time.sleep(1)
            self.update_pidvalues()
            self.update_temperatures()
            self.update_DO()
            
    def stop(self,):
        self.quit = True
        #self.DATAQ.close()
        #self.omega.all_off()
        for key in self.omegaAO.keys():
            try:
                self.omegaAO[key].close()
            except:
                pass
        self.omegaDO.close()

class MainDGIO(threading.Thread):
    """ Temperature reader """
    def __init__(self):
        logging.info('MainDGIO class started')
        threading.Thread.__init__(self)
        #from digitalinot import ValveControl
        self.quit = False
        self.codenames = ['tabs_guard_valve_heating',
                     'tabs_floor_valve_heating',
                     'tabs_ceiling_valve_heating',
                     'tabs_guard_valve_cooling',
                     'tabs_floor_valve_cooling',
                     'tabs_ceiling_valve_cooling',
                     'tabs_cooling_valve_cooling',
                     ]
        #sockname = 'tabs_valve'
        #codenames = socketinfo.INFO[sockname]['codenames']
        #self.PullSocket = DateDataPullSocket(sockname, self.codenames, timeouts=[60.0]*len(self.codenames), port = socketinfo.INFO[sockname]['port'])
        #self.PullSocket.start()
        self.VC = ValveControl(self.codenames)
        self.VC.daemon = True
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
        #self.db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=self.codenames)
        #self.db_logger.start()
    def run(self,):
        i = 0
        while not self.quit and self.VC.isAlive():
            try:
                #print(i)
                time.sleep(2)
                for name in self.codenames:
                    v = self.loggers[name].read_value()
                    #print('Status: ', name , v)
                    #livesocket.set_point_now(name, v)
                    #self.PullSocket.set_point_now(name, v)
                    if self.loggers[name].read_trigged():
                        if __name__ == '__main__':
                            print('Log: ', i, name, v)
                        #self.db_logger.enqueue_point_now(name, v)
                        self.loggers[name].clear_trigged()
            except (KeyboardInterrupt, SystemExit):
                self.quit = True
                pass
                #self.VC.stop()
                #report error and proceed
            i += 1
        self.stop()
    def stop(self):
        self.quit = True
        self.VC.stop()
        #self.PullSocket.stop()
        #self.db_logger.stop()
        for key in self.codenames:
            self.loggers[key].status['quit'] = True

if __name__ == '__main__':
    
    DGIO = MainDGIO()
    time.sleep(3)
    DGIO.start()
    
    while DGIO.isAlive():
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            DGIO.quit = True
    print('END')
    
    #codenames = ['tabs_guard_valve_heating',
    #                 'tabs_floor_valve_heating',
    #                 'tabs_ceiling_valve_heating',
    #                 'tabs_guard_valve_cooling',
    #                 'tabs_floor_valve_cooling',
    #                 'tabs_ceiling_valve_cooling',
    #                 'tabs_cooling_valve_cooling',
    #                 ]
    #VC = ValveControl(codenames)
    #VC.omegaAO['tabs_cooling_valve_cooling'].set_value(0)
    #VC.omegaAO['tabs_cooling_valve_cooling'].get_value()