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
from PyExpLabSys.auxiliary.TC_Calculator import TC_Calculator
import PyExpLabSys.drivers.agilent_34970A as Agilent
#import PyExpLabSys.drivers.kampstrup as kampstrup

import socketinfo
import credentials
ContinuousLogger.host = credentials.dbhost
ContinuousLogger.database = credentials.dbname

class MultiplexReader(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        self.codenames = codenames
        threading.Thread.__init__(self)
        port = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
        self.Agilent = Agilent.Agilent34970ADriver(port = port)
        self.SYSTEMS = {}
        for sy in ['tabs_guard', 'tabs_floor', 'tabs_ceiling', 'tabs_cooling', 'tabs_ice']:
            self.SYSTEMS[sy] = {'temperature_inlet': None, # float in C
                                'temperature_outlet': None, # float in C
                                'temperature_setpoint': None, # float in C
                                'valve_cooling': None, # float 0-1
                                'valve_heating': None, # float 0-1
                                'pid_value': None, # float -1-1
                                'water_flow': None} # float in l/min
        self.DATA = {}
        for key in self.codenames:
            self.DATA[key] = 0.0
        self.chnumbers = self.Agilent.read_scan_list()
        self.named_channel_list = {101:'tabs_ceiling_temperature_delta',
                                   #102: 'tabs_ceiling_temperature_inlet',
                                   103: 'tabs_floor_temperature_delta',
                                   #104: 'tabs_floor_temperature_inlet', 
                                   #105: 'tabs_ceiling-pipe surface',
                                   106: 'tabs_room_temperature_aircenter110',
                                   #107: 'tabs_ceiling_temperature_btw',
                                   #108: 'tabs_ceiling_temperature_ontop',
                                   #109: 'tabs_ceiling_temperature_deltaup',
                                   #109: 'tabs_ceiling_temperature_deltaup',
                                   111: 'tabs_room_temperature_aircenter001',
                                   }
        

        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        return_val = None
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel in self.named_channel_list.keys():
                return_val = self.DATA[self.named_channel_list[channel]]
        return return_val

    def update_values(self,):
        try:
            response = self.Agilent.read_single_scan()
            chs = response[2::4]
            values = response[0::4]
            self.ttl = 100
        except:
            print('Cant connect to agilent')
            response = None
        if response != None:
            for ch, value in zip(chs, values):
                if ch in self.named_channel_list.keys():
                    codename = self.named_channel_list[ch]
                    if codename in ['tabs_ceiling_temperature_delta', 'tabs_floor_temperature_delta']:
                        self.DATA[codename] = TC_Calculator(value*1000, No=3, tctype='K')
                    else:
                        self.DATA[codename] = value
                    print(codename, self.DATA[codename])

    def run(self):
        while not self.quit:            
            self.update_values()
            time.sleep(20)
            
    def stop(self,):
        self.quit = True
        self.Agilent.close()


#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)


class MainMultilogger(threading.Thread):
    """ Temperature reader """
    def __init__(self,):
        threading.Thread.__init__(self)
        #from datalogger import TemperatureReader
        self.quit = False
        self.codenames = ['tabs_ceiling_temperature_delta',
                          'tabs_floor_temperature_delta',]
        self.multiplex_reader = MultiplexReader(self.codenames)
        self.multiplex_reader.start()
        #omega_temperature.update_values()
        
        time.sleep(3.5)
        
        chlist = {'tabs_ceiling_temperature_delta': 101,
                  'tabs_floor_temperature_delta': 103,}
        self.loggers = {}
        for key in self.codenames:
            self.loggers[key] = ValueLogger(self.multiplex_reader, comp_val = 0.2, maximumtime=60,
                                            comp_type = 'lin', channel = chlist[key])
            self.loggers[key].start()
        
        #livesocket = LiveSocket('tabs_temperature_logger', codenames, 2)
        #livesocket.start()
        sockname = 'tabs_multiplexer'
        self.PullSocket = DateDataPullSocket(sockname, self.codenames, timeouts=[60.0]*len(self.codenames), port = socketinfo.INFO[sockname]['port'])
        self.PullSocket.start()
        
        self.db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=self.codenames)
        self.db_logger.start()
    
    def run(self,):
        i = 0
        while not self.quit:
            try:
                #print(i)
                time.sleep(1)
                for name in self.codenames:
                    v = self.loggers[name].read_value()
                    #livesocket.set_point_now(name, v)
                    self.PullSocket.set_point_now(name, v)
                    #print(i, name, v)
                    if self.loggers[name].read_trigged():
                        #print(i, name, v)
                        self.db_logger.enqueue_point_now(name, v)
                        self.loggers[name].clear_trigged()
            except (KeyboardInterrupt, SystemExit):
                pass
                #self.omega_temperature.close()
                #report error and proceed
            i += 1
    def stop(self):
        self.quit = True
        self.multiplex_reader.stop()
        self.db_logger.stop()
        self.PullSocket.stop()
        for key in self.codenames:
            self.loggers[key].status['quit'] = True

if __name__ == '__main__':
    MML = MainMultilogger()
    MML.start()
    
    while MML.isAlive():
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            MML.stop()
    print('END')
    
