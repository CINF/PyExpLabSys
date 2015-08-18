# -*- coding: utf-8 -*-
# !/usr/bin/env python
# pylint: disable=C0301,R0904, C0103
""" Pressure and temperature logger """

from __future__ import print_function

import sys
sys.path.insert(1, '/home/pi/PyExpLabsys')
sys.path.insert(2, '../..')

import threading
import time
import logging
from PyExpLabSys.common.loggers import ContinuousLogger
import credentials
ContinuousLogger.host = credentials.dbhost
ContinuousLogger.database = credentials.dbname
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.auxiliary.pid import PID
#import PyExpLabSys.drivers.omegabus as omegabus
import PyExpLabSys.drivers.omega_cni as omega_CNi32
#import PyExpLabSys.drivers.kampstrup as kampstrup


#==============================================================================
# class OldTempReader(threading.Thread):
#     """ Temperature reader """
#     def __init__(self, omegabus):
#         threading.Thread.__init__(self)
#         self.omegabus = omegabus
#         self.ttl = 20
#         self.temperature = None
#         self.quit = False
# 
#     def value(self):
#         """ Read the temperaure """
#         self.ttl = self.ttl - 1
#         if self.ttl < 0:
#             self.quit = True
#         return(self.temperature)
# 
#     def run(self):
#         while not self.quit:
#             self.ttl = 20
#             time.sleep(1)
#             self.temperature = self.omegabus.ReadValue(2)
#==============================================================================


class NGTempReader(threading.Thread):
    """ Temperature reader """
    def __init__(self, omega):
        threading.Thread.__init__(self)
        self.omega = omega
        self.ttl = 20
        self.temperature = None
        self.quit = False

    def value(self):
        """ Read the temperaure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        return(self.temperature)

    def run(self):
        while not self.quit:
            self.ttl = 20
            time.sleep(1)
            self.temperature = self.omega.read_temperature(address = 2)

class TABS_Temperature(threading.Thread):
    """ class for control of the TABS test room """
    def __init__(self, Multical, Omegas):
        threading.Thread.__init__(self)
        self.Multical = Multical
        self.Omegas = Omegas
        self.temperatures
    def  update_temperatures(self,):
        self.update()
    def run(self):
        self.update_temperatures()
        self.update_flows
        
class TemperatureReader(threading.Thread):
    """ Temperature reader """
    def __init__(self,):
        threading.Thread.__init__(self)
        self.OmegaPortsDict = {}
        self.OmegaPortsDict['tabs_guard_temperature'] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWEA5HJ-if00-port0'
        self.OmegaPortsDict['tabs_floor_temperature'] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTYIWHC9-if00-port0'
        self.OmegaPortsDict['tabs_ceiling_temperature'] = '/dev/serial/by-id/usb-OMEGA_ENGINEERING_12.34-if00'
        self.OmegaPortsDict['tabs_cooling_temperature'] = '/dev/serial/by-id/usb-OMEGA_ENGINEERING_12.34-if01'
        
        #self.OmegaPortsDict['tabs_guard_temperature'] = '/dev/ttyUSB1'
        #self.OmegaPortsDict['tabs_floor_temperature'] = '/dev/ttyUSB0'
        self.OmegaPortsDict['tabs_ceiling_temperature'] = '/dev/ttyACM0'
        self.OmegaPortsDict['tabs_cooling_temperature'] = '/dev/ttyACM2'
        
        self.OmegaCommStnd = {}
        self.OmegaCommStnd['tabs_guard_temperature'] = 'rs485'
        self.OmegaCommStnd['tabs_floor_temperature'] = 'rs485' #add 2
        self.OmegaCommStnd['tabs_ceiling_temperature'] = 'rs232'
        self.OmegaCommStnd['tabs_cooling_temperature'] = 'rs232'
        
        self.OmegaCommAdd = {}
        self.OmegaCommAdd['tabs_guard_temperature'] = 1
        self.OmegaCommAdd['tabs_floor_temperature'] = 1
        
        self.OmegaDict = {}
        for key in self.OmegaPortsDict.keys():
            print('Initializing: ' + key)
            self.OmegaDict[key] = omega_CNi32.ISeries(self.OmegaPortsDict[key], 9600, comm_stnd=self.OmegaCommStnd[key])
            
        self.temperatures = {'tabs_guard_temperature': None,
                             'tabs_floor_temperature': None,
                             'tabs_ceiling_temperature': None,
                             'tabs_cooling_temperature': None}
        self.quit = False
        self.ttl = 20
    def setup_rtd(self, name):
        #print('Format: ' + str(value.command('R08') ) )
        print('Intup Type: ' + self.OmegaDict[name].command('R07'))
        print('Reading conf: ' + self.OmegaDict[name].command('R08'))
        if name == 'tabs_guard_temperature':
            pass
        elif name == 'tabs_floor_temperature':
            pass
        elif name == 'tabs_ceiling_temperature':
            #self.OmegaDict[name].command('W0701')
            #self.OmegaDict[name].reset_device()
            pass
        elif name == 'tabs_cooling_temperature':
            
            pass

    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel == 0:
                return_val = self.temperatures['tabs_guard_temperature']
            if channel == 1:
                return_val = self.temperatures['tabs_floor_temperature']
            if channel == 2:
                return_val = self.temperatures['tabs_ceiling_temperature']
            if channel == 3:
                return_val = self.temperatures['tabs_cooling_temperature']
        return return_val
    def update_values(self,):
        for key, value in self.OmegaDict.items():
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
                    pass
                self.temperatures[key] = v
                self.ttl = 50
            except IndexError:
                print("av")
            except ValueError, TypeError:
                self.temperatures[key] = None
        #print(self.temperatures)

    def run(self):
        while not self.quit:
            time.sleep(2)
            self.update_values()
            
    def close(self,):
        self.quit = True
        for key, value in self.OmegaDict.items():
            value.close()

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)



if __name__ == '__main__':
    omega_temperature = TemperatureReader()
    omega_temperature.start()
    #omega_temperature.update_values()
    
    time.sleep(1.5)
    
    codenames = ['tabs_guard_temperature',
                 'tabs_floor_temperature',
                 'tabs_ceiling_temperature',
                 'tabs_cooling_temperature',
                 ]
    loggers = {}
    loggers['tabs_guard_temperature'] = ValueLogger(omega_temperature, comp_val = 0.9, maximumtime=60,
                                        comp_type = 'lin', channel = 0)
    loggers['tabs_guard_temperature'].start()
    
    loggers['tabs_floor_temperature'] = ValueLogger(omega_temperature, comp_val = 0.9, maximumtime=60,
                                        comp_type = 'lin', channel = 1)
    loggers['tabs_floor_temperature'].start()
    
    loggers['tabs_ceiling_temperature'] = ValueLogger(omega_temperature, comp_val = 0.9, maximumtime=60,
                                        comp_type = 'lin', channel = 2)
    loggers['tabs_ceiling_temperature'].start()
    
    loggers['tabs_cooling_temperature'] = ValueLogger(omega_temperature, comp_val = 0.9, maximumtime=60,
                                        comp_type = 'lin', channel = 3)
    loggers['tabs_cooling_temperature'].start()
    
    #livesocket = LiveSocket('tabs_temperature_logger', codenames, 2)
    #livesocket.start()
    
    #socket = DateDataPullSocket('tabs_temperature', codenames, timeouts=[1.0]*len(codenames))
    #socket.start()
    
    db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=codenames)
    print('Hostname of db logger: ' + db_logger.host)
    db_logger.start()
    i = 0
    while omega_temperature.isAlive():
        try:
            #print(i)
            time.sleep(10)
            for name in codenames:
                v = loggers[name].read_value()
                #livesocket.set_point_now(name, v)
                #socket.set_point_now(name, v)
                if loggers[name].read_trigged():
                    print(i, name, v)
                    db_logger.enqueue_point_now(name, v)
                    loggers[name].clear_trigged()
        except (KeyboardInterrupt, SystemExit):
            omega_temperature.close()
            #report error and proceed
        i += 1
    print(i)
    