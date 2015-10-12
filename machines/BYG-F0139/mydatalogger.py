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
from PyExpLabSys.common.loggers import ContinuousLogger


from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
#from PyExpLabSys.auxiliary.pid import PID
import PyExpLabSys.drivers.omega_cni as omega_CNi32
#import PyExpLabSys.drivers.kampstrup as kampstrup

import socketinfo
import credentials
ContinuousLogger.host = credentials.dbhost
ContinuousLogger.database = credentials.dbname


class RunningMean(object):
    def __init__(length):
        self.list = list(length)

class TemperatureReader(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        threading.Thread.__init__(self)
        self.SYSTEMS = {}
        for sy in ['tabs_guard', 'tabs_floor', 'tabs_ceiling', 'tabs_cooling', 'tabs_ice']:
            self.SYSTEMS[sy] = {'temperature_inlet': None, # float in C
                                'temperature_outlet': None, # float in C
                                'temperature_setpoint': None, # float in C
                                'valve_cooling': None, # float 0-1
                                'valve_heating': None, # float 0-1
                                'pid_value': None, # float -1-1
                                'water_flow': None} # float in l/min
        self.OmegaPortsDict = {}
        self.OmegaPortsDict['tabs_guard_temperature_inlet'] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWEA5HJ-if00-port0'
        self.OmegaPortsDict['tabs_floor_temperature_inlet'] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTYIWHC9-if00-port0'
        self.OmegaPortsDict['tabs_ceiling_temperature_inlet'] = '/dev/serial/by-id/usb-OMEGA_ENGINEERING_12.34-if00'
        self.OmegaPortsDict['tabs_cooling_temperature_inlet'] = '/dev/serial/by-id/usb-OMEGA_ENGINEERING_12.34-if01'
        
        #self.OmegaPortsDict['tabs_guard_temperature_inlet'] = '/dev/ttyUSB1'
        #self.OmegaPortsDict['tabs_floor_temperature_inlet'] = '/dev/ttyUSB0'
        self.OmegaPortsDict['tabs_ceiling_temperature_inlet'] = '/dev/ttyACM0'
        self.OmegaPortsDict['tabs_cooling_temperature_inlet'] = '/dev/ttyACM1'
        
        self.OmegaCommStnd = {}
        self.OmegaCommStnd['tabs_guard_temperature_inlet'] = 'rs485'
        self.OmegaCommStnd['tabs_floor_temperature_inlet'] = 'rs485' #add 2
        self.OmegaCommStnd['tabs_ceiling_temperature_inlet'] = 'rs232'
        self.OmegaCommStnd['tabs_cooling_temperature_inlet'] = 'rs232'
        
        self.OldValue = {}
        self.OldValue['tabs_guard_temperature_inlet'] = None
        self.OldValue['tabs_floor_temperature_inlet'] = None
        self.OldValue['tabs_ceiling_temperature_inlet'] = None
        self.OldValue['tabs_cooling_temperature_inlet'] = None
        
        self.OffSet = {}
        self.OffSet['tabs_guard_temperature_inlet'] = 0.62
        self.OffSet['tabs_floor_temperature_inlet'] = 1.32
        self.OffSet['tabs_ceiling_temperature_inlet'] = 0.30
        self.OffSet['tabs_cooling_temperature_inlet'] = -0.49
        
        self.OmegaCommAdd = {}
        self.OmegaCommAdd['tabs_guard_temperature_inlet'] = 1
        self.OmegaCommAdd['tabs_floor_temperature_inlet'] = 1
        
        self.OmegaDict = {}
        for key in codenames:
            #print('Initializing: ' + key)
            self.OmegaDict[key] = omega_CNi32.ISeries(self.OmegaPortsDict[key], 9600, comm_stnd=self.OmegaCommStnd[key])
            
        #self.temperatures = {'tabs_guard_temperature': None,
        #                     'tabs_floor_temperature': None,
        #                     'tabs_ceiling_temperature': None,
        #                     'tabs_cooling_temperature': None}
        self.quit = False
        self.ttl = 20

    def setup_rtd(self, name):
        #print('Format: ' + str(value.command('R08') ) )
        print('Intup Type: ' + self.OmegaDict[name].command('R07'))
        print('Reading conf: ' + self.OmegaDict[name].command('R08'))
        if name == 'tabs_guard_temperature_inlet':
            pass
        elif name == 'tabs_floor_temperature_inlet':
            pass
        elif name == 'tabs_ceiling_temperature_inlet':
            #self.OmegaDict[name].command('W0701')
            #self.OmegaDict[name].reset_device()
            pass
        elif name == 'tabs_cooling_temperature_inlet':
            
            pass

    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            me = 'temperature_inlet'
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
        return return_val

    def update_values(self,):
        for key, value in self.OmegaDict.items():
            _key = str(key).rsplit('_')
            sy = _key[0]+'_' + _key[1]
            me = _key[2]+'_' + _key[3]
            #print(sy, me)
            try:
                #print("Omega: {}".format(key))
                if self.OmegaCommStnd[key] == 'rs485':
                    v = value.read_temperature(address=self.OmegaCommAdd[key])
                    #print('Temp: ' + str(self.temperatures[key]) )
                elif self.OmegaCommStnd[key] == 'rs232':
                    v = value.read_temperature()
                    #print('Temp: ' + str(self.temperatures[key]) )
                    #print('Format: ' + str(value.command('R08') ) )
                else:
                    self.SYSTEMS[sy][me] = None
                new_val = v + self.OffSet[key]
                old_val = self.OldValue[key]
                if new_val == None:
                    pass
                elif old_val == None:
                    old_val = new_val
                    self.SYSTEMS[sy][me] = new_val
                elif abs(new_val - old_val) < 0.5:
                    old_val = new_val
                    self.SYSTEMS[sy][me] = new_val
                else:
                    pass
                self.ttl = 50
            except IndexError:
                print("av")
            except ValueError, TypeError:
                self.SYSTEMS[sy][me] = None
        #print(self.temperatures)

    def run(self):
        while not self.quit:
            time.sleep(2)
            self.update_values()
            
    def stop(self,):
        self.quit = True
        for key, value in self.OmegaDict.items():
            value.close()

#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)


class MainDatalogger(threading.Thread):
    """ Temperature reader """
    def __init__(self,):
        threading.Thread.__init__(self)
        #from datalogger import TemperatureReader
        self.quit = False
        self.codenames = ['tabs_guard_temperature_inlet',
                     'tabs_floor_temperature_inlet',
                     'tabs_ceiling_temperature_inlet',
                     'tabs_cooling_temperature_inlet',
                     ]
        self.omega_temperature = TemperatureReader(self.codenames)
        self.omega_temperature.start()
        #omega_temperature.update_values()
        
        time.sleep(1.5)
        
        chlist = {'tabs_guard_temperature_inlet': 0, 'tabs_floor_temperature_inlet': 1, 'tabs_ceiling_temperature_inlet': 2, 'tabs_cooling_temperature_inlet': 3}
        self.loggers = {}
        for key in self.codenames:
            self.loggers[key] = ValueLogger(self.omega_temperature, comp_val = 0.2, maximumtime=60,
                                            comp_type = 'lin', channel = chlist[key])
            self.loggers[key].start()
        
        #livesocket = LiveSocket('tabs_temperature_logger', codenames, 2)
        #livesocket.start()
        sockname = 'tabs_temperatures'
        self.PullSocket = DateDataPullSocket(sockname, self.codenames, timeouts=[60.0]*len(self.codenames), port = socketinfo.INFO[sockname]['port'])
        self.PullSocket.start()
        
        self.db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=self.codenames)
        self.db_logger.start()
    
    def run(self,):
        i = 0
        while not self.quit and self.omega_temperature.isAlive():
            try:
                #print(i)
                time.sleep(1)
                for name in self.codenames:
                    v = self.loggers[name].read_value()
                    #livesocket.set_point_now(name, v)
                    self.PullSocket.set_point_now(name, v)
                    if self.loggers[name].read_trigged():
                        if __name__ == '__main__':
                            print('Log: ', i, name, v)
                        self.db_logger.enqueue_point_now(name, v)
                        self.loggers[name].clear_trigged()
            except (KeyboardInterrupt, SystemExit):
                pass
                #self.omega_temperature.close()
                #report error and proceed
            i += 1
        self.stop()
    def stop(self):
        self.quit = True
        self.omega_temperature.stop()
        self.db_logger.stop()
        self.PullSocket.stop()
        for key in self.codenames:
            self.loggers[key].status['quit'] = True

if __name__ == '__main__':
    MDL = MainDatalogger()
    time.sleep(3)
    MDL.start()
    
    while MDL.isAlive():
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            MDL.stop()
    #print('END')
    
