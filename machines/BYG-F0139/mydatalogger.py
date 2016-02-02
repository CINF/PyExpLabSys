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

import pykamtest

import socketinfo
import credentials
ContinuousLogger.host = credentials.dbhost
ContinuousLogger.database = credentials.dbname

logging.basicConfig(filename="logger_mydatalogger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)


class WaterTemperatureReader(threading.Thread):
    """ Temperature reader """
    def __init__(self,):
        logging.info('WaterTemperatureReader class started')
        threading.Thread.__init__(self)
        self.chlist = {'tabs_guard_temperature_inlet': 0,
                   'tabs_guard_temperature_outlet': 1,
                   'tabs_guard_temperature_delta': 2,
                   'tabs_floor_temperature_inlet': 3,
                   'tabs_floor_temperature_outlet': 4,
                   'tabs_floor_temperature_delta': 5,                   
                   'tabs_ceiling_temperature_inlet': 6,
                   'tabs_ceiling_temperature_outlet': 7,
                   'tabs_ceiling_temperature_delta': 8,
                   'tabs_guard_water_flow': 9,
                   'tabs_floor_water_flow': 10,
                   'tabs_ceiling_water_flow': 11,}
        self.DATA= {}
        for key in self.chlist.keys():
            self.DATA[key] = None
        port = '/dev/serial/by-id/usb-Silicon_Labs_Kamstrup_M-Bus_Master_MultiPort_250D_131751521-if00-port0'
        self.MCID = {}
        self.MCID['tabs_guard_'] = 13
        self.MCID['tabs_floor_'] = 15
        self.MCID['tabs_ceiling_'] = 14
        
        self.MC302device = pykamtest.kamstrup(serial_port=port)

        self.quit = False
        self.ttl = 500



    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel in self.chlist.values():
                for key, value in self.chlist.items():
                    if channel == value:
                        return_val = self.DATA[key]
            else:
                return_val = None
        return return_val

    def update_values(self,):
        for key, ID in self.MCID.items():
            try:
                v = self.MC302device.read_water_temperature(ID)
                #print(v)
                if len(v) == 4:
                    self.DATA[key +'temperature_inlet'] = v['inlet']
                    self.DATA[key +'temperature_outlet'] = v['outlet']
                    self.DATA[key +'temperature_delta'] = v['diff']
                    self.DATA[key +'water_flow'] = v['flow']
                else:
                    logging.warn('Does not get 4 values from MV302')
                    self.DATA[key +'temperature_inlet'] = None
                    self.DATA[key +'temperature_outlet'] = None
                    self.DATA[key +'temperature_delta'] = None
                    self.DATA[key +'water_flow'] = None
                self.ttl = 500
            except IndexError:
                logging.warn('IndexError')
                #print("av")
                pass
            except ValueError, TypeError:
                logging.warn('ValueError, TypeError')
                self.DATA[key +'temperature_inlet'] = None
                self.DATA[key +'temperature_outlet'] = None
                self.DATA[key +'temperature_delta'] = None
                self.DATA[key +'water_flow'] = None
            time.sleep(2)
            #print(self.temperatures)

    def run(self):
        while not self.quit:
            try:
                self.update_values()
            except:
                logging.warn('except, all')
            time.sleep(2)
        self.quit = True
            
    def stop(self,):
        self.quit = True
        try:
            self.MC302device.close()
        except:
            logging.warn('Except portNotOpenError, proberly closed by other temperature reader')

class TemperatureReader(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        logging.info('TemperatureReader class started')
        threading.Thread.__init__(self)
        """self.SYSTEMS = {}
        for sy in ['tabs_guard', 'tabs_floor', 'tabs_ceiling', 'tabs_cooling', 'tabs_ice', 'tabs_room']:
            self.SYSTEMS[sy] = {'temperature_inlet': None, # float in C
                                'temperature_outlet': None, # float in C
                                'temperature_setpoint': None, # float in C
                                'temperature_control': None, # float in C
                                'valve_cooling': None, # float 0-1
                                'valve_heating': None, # float 0-1
                                'pid_value': None, # float -1-1
                                'water_flow': None} # float in l/min
                                """
        self.OldValue = {}
        self.OldValue['tabs_guard_temperature_control'] = None
        self.OldValue['tabs_room_temperature_control'] = None
        #self.OldValue['tabs_ceiling_temperature_inlet'] = None
        self.OldValue['tabs_cooling_temperature_inlet'] = None
        
        self.OffSet = {}
        self.OffSet['tabs_room_temperature_control'] = 27.0-34.8 # 0.62
        self.OffSet['tabs_guard_temperature_control'] = 23.5-28.3 #1.32
        #self.OffSet['tabs_ceiling_temperature_inlet'] = 0.30
        self.OffSet['tabs_cooling_temperature_inlet'] = 0 #-0.49
        
        self.OmegaCommAdd = {}
        self.OmegaCommAdd['tabs_guard_temperature_control'] = 1
        self.OmegaCommAdd['tabs_room_temperature_control'] = 1
        
        self.OmegaDict = {}
        self.OmegaDict['tabs_room_temperature_control'] = omega_CNi32.ISeries('/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWEA5HJ-if00-port0', 9600, comm_stnd='rs485', address = 1)
        self.OmegaDict['tabs_guard_temperature_control'] = omega_CNi32.ISeries('/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTYIWHC9-if00-port0', 9600, comm_stnd='rs485', address = 1)
        self.OmegaDict['tabs_cooling_temperature_inlet'] = omega_CNi32.ISeries('/dev/serial/by-id/usb-OMEGA_ENGINEERING_12.34-if00', 9600, comm_stnd='rs232')
        
        self.SYSTEMS = {}
        for key in self.OmegaDict.keys():
            self.SYSTEMS[key] = None
            
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
            if channel == 0:
                return_val = self.SYSTEMS['tabs_guard_temperature_control']
            elif channel == 1:
                return_val = self.SYSTEMS['tabs_room_temperature_control']
            elif channel == 3:
                return_val = self.SYSTEMS['tabs_cooling_temperature_inlet']
        return return_val

    def update_values(self,):
        for key, value in self.OmegaDict.items():
            #print(sy, me)
            try:
                #print("Omega: {}".format(key))
                v = value.read_temperature()
                if type(v) == type(0.0):
                    new_val = v + self.OffSet[key]
                old_val = self.OldValue[key]
                if new_val == None:
                    pass
                elif old_val == None:
                    old_val = new_val
                    self.SYSTEMS[key] = new_val
                elif abs(new_val - old_val) < 0.5:
                    old_val = new_val
                    self.SYSTEMS[key] = new_val
                else:
                    pass
                self.ttl = 50
            except IndexError:
                logging.warn('IndexError')
            except ValueError:
                logging.warn('ValueError')
                self.SYSTEMS[key] = None
            except TypeError:
                logging.warn('TypeError')
                self.SYSTEMS[key] = None
        #print(self.temperatures)

    def run(self):
        while not self.quit:
            time.sleep(2)
            self.update_values()
            
    def stop(self,):
        self.quit = True
        for key, value in self.OmegaDict.items():
            try:
                value.close()
            except:
                pass

#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)


class MainDatalogger(threading.Thread):
    """ Temperature reader """
    def __init__(self,):
        logging.info('MainDatalogger class started')
        threading.Thread.__init__(self)
        #from datalogger import TemperatureReader
        self.quit = False
        self.codenames = ['tabs_guard_temperature_inlet',
                     'tabs_floor_temperature_inlet',
                     'tabs_ceiling_temperature_inlet',
                     'tabs_cooling_temperature_inlet',
                     ]
        self.MC302 = WaterTemperatureReader()
        self.MC302.start()
        self.codenames = [
                     'tabs_cooling_temperature_inlet',
                     ]
        self.omega_temperature = TemperatureReader(['tabs_cooling_temperature_inlet',])
        self.omega_temperature.daemon = True
        self.omega_temperature.start()
        #omega_temperature.update_values()
        
        time.sleep(1.5)
        
        chlist = {'tabs_guard_temperature_control': 0,
                  'tabs_room_temperature_control': 1,
                  #'tabs_ceiling_temperature_inlet': 2,
                  'tabs_cooling_temperature_inlet': 3}
        self.loggers = {}
        for key in chlist.keys():
            self.loggers[key] = ValueLogger(self.omega_temperature, comp_val = 0.2, maximumtime=300,
                                            comp_type = 'lin', channel = chlist[key])
            self.loggers[key].start()
        chlist = {'tabs_guard_temperature_inlet': 0,
                   'tabs_guard_temperature_outlet': 1,
                   'tabs_guard_temperature_delta': 2,
                   'tabs_floor_temperature_inlet': 3,
                   'tabs_floor_temperature_outlet': 4,
                   'tabs_floor_temperature_delta': 5,                   
                   'tabs_ceiling_temperature_inlet': 6,
                   'tabs_ceiling_temperature_outlet': 7,
                   'tabs_ceiling_temperature_delta': 8,
                   'tabs_guard_water_flow': 9,
                   'tabs_floor_water_flow': 10,
                   'tabs_ceiling_water_flow': 11,}
        for key in chlist.keys():
            self.loggers[ key] = ValueLogger(self.MC302, comp_val = 0.2, maximumtime=300,
                                            comp_type = 'lin', channel = chlist[key])
            self.loggers[key].start()
        self.codenames = self.loggers.keys()
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
                for name in self.loggers.keys():
                    v = self.loggers[name].read_value()
                    #livesocket.set_point_now(name, v)
                    if v != None and v != 0:
                        self.PullSocket.set_point_now(name, v)
                        if self.loggers[name].read_trigged():
                            if __name__ == '__main__':
                                print('Log: ', i, name, v)
                            self.db_logger.enqueue_point_now(name, v)
                            self.loggers[name].clear_trigged()
                        else:
                            if __name__ == '__main__':
                                print('STA: ', i, name, v)
            except (KeyboardInterrupt, SystemExit):
                pass
                #self.omega_temperature.close()
                #report error and proceed
            i += 1
        self.stop()
        
    def stop(self):
        self.quit = True
        self.omega_temperature.stop()
        self.MC302.stop()
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
            MDL.quit = True
    print('END')
    
    #omega_temperature = TemperatureReader(['tabs_cooling_temperature_inlet',])
    #omega_temperature.update_values()
    #print(omega_temperature.value(3))
    #omega_temperature.OmegaDict['tabs_cooling_temperature_inlet'].read_temperature()
    
