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
import SocketServer
SocketServer.UDPServer.allow_reuse_address = True


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

Setting_channel_list = {'tabs_ceiling_temperature_delta': 101,
                  'tabs_ceiling_temperature_deltaref': 102,
                  'tabs_floor_temperature_delta': 103,
                  'tabs_floor_temperature_deltaref': 104,
                  #'Tpipe_up': 105, # Tpipe_up
                  'tabs_room_temperature_aircenter110': 106,
                  #'tabs_ceiling_temperature_up': 107, # Tceil2_1up
                  #'Tconcsus_1up': 108, # Tconcsus_1up
                  #'DT_1up109': 109, # DT_1up109
                  #'Tsurref_1up': 110, # Tsurref_1up
                  'tabs_room_temperature_aircenter010': 111,
                  #'DT_2up112': 112, # DT_2up112
                  #'Tsurref_2up': 113, # Tsurref_2up
                  #'DTfloor1_up': 114, # DTfloor1_up
                  #'Tref1_up': 115, # Tref1_up
                  #'Tpipe_low': 116, # Tpipe_low
                  #'DT_1flow117': 117, # DT_1flow117
                  #'Tsurref_1low': 118, # Tsurref_1low
                  #'DT_2low119': 119, # DT_2low119
                  #'Tsurref_2low': 120, # Tsurref_2low
                  #'Flow_up121': 121, # Flow_up121
                  #'Flow_low122': 122, # Flow_low122
                  
                  #'None': 201
                  #'Top2_room_1.1m': 202, # Top2_room_1.1m
                  #'None': 203,
                  #'Tsur2_room_wall2': 204, # Tsur2_room_wall2
                  'tabs_room_temperature_aircenter170': 205, # Tair4_room_1.7m
                  'tabs_room_temperature_aircenter060': 206, # Tair2_room_0.6m
                  #'Tsur1_room_wall1': 207, # Tsur1_room_wall1
                  #'Tsur4_room_ceiling1': 208, # Tsur4_room_ceiling1
                  #'None': 209,
                  #'None': 210,
                  #'Tsur5_room_ceiling2': 211, # Tsur5_room_ceiling2
                  #'None': 212,
                  'tabs_room_temperature_aircenter355': 213, # air_room_0.1mTOP
                  #'Tsur3_room_floor': 214, # Tsur3_room_floor
                  #'Top1_room_0.6': 215, # Top1_room_0.6
                  #'Tsur6_room_ceiling3': 216, # Tsur6_room_ceiling3
                  #'HeatFlow4_floor': 217, # HeatFlow4_floor
                  #'DTfloor1_low': 218, # DTfloor1_low
                  #'Tref1_low': 219, # Tref1_low
                  #'HeatFlow3_ceiling': 220, # HeatFlow3_ceiling
                  #'None': 221,
                  #'None': 222,
                  'tabs_guard_temperature_airfloor': 301, # Tair1_guard
                  'tabs_guard_temperature_airceiling': 302, # Tair2_guard
                  'tabs_guard_temperature_airwallsouth': 303, # Tair3_guard
                  'tabs_guard_temperature_airwallnorth': 304, # Tair4_guard
                  'tabs_guard_temperature_airwalleast': 305, # Tair5_guard
                  'tabs_guard_temperature_airwallwest': 306, # Tair6_guard
                  #'tabs_wallsouth_temperature_delta': 307, # DTwall1307
                  #'HeatFlow2_ceiling': 308, # HeatFlow2_ceiling
                  #'tabs_wallnorth_temperature_delta': 309, # DTwall2309
                  #'tabs_wallnorth_temperature_deltaref': 310, # Twallref2
                  #'tabs_walleast_temperature_delta': 311, # DTwall3311
                  #'tabs_walleast_temperature_deltaref': 312, # Twallref3
                  #'tabs_wallwest_temperature_delta': 313, # DTwall4313
                  #'tabs_wallwest_temperature_deltaref': 314, # Twallref4
                  #'DTlen_gaurdup': 315, # DTlen_gaurdup
                  #'Treflen_guardup': 316, # Treflen_guardup
                  #'Treflen_guardup1': 317, # Treflen_guardup1
                  #'Treflen_guardup2': 318, # Treflen_guardup2
                  #'None': 319,
                  #'HeatFlow1_ceiling': 320, # HeatFlow1_ceiling
                  #'None': 321,
                  #'None': 322,
                  }

class MultiplexReader(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        self.codenames = codenames
        threading.Thread.__init__(self)
        port = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
        self.Agilent = Agilent.Agilent34970ADriver(port = port)
        self.DATA = {}
        for key in self.codenames:
            self.DATA[key] = 0.0
        self.chnumbers = self.Agilent.read_scan_list()
        self.named_channel_list = Setting_channel_list
        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read the pressure """
        #self.ttl = self.ttl - 1
        return_val = None
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel in self.named_channel_list.values():
                for k, v in self.named_channel_list.items():
                    if channel == v:
                        return_val = self.DATA[k]
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
                #print(ch, value)
                if ch in self.named_channel_list.values():
                    for k, v in self.named_channel_list.items():
                        if ch == v:
                            codename = k
                            break
                    if codename in ['tabs_ceiling_temperature_delta', 'tabs_floor_temperature_delta']:
                        self.DATA[codename] = TC_Calculator(value*1000, No=3, tctype='K')
                    else:
                        self.DATA[codename] = value
                    #print(codename, self.DATA[codename])

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
                          'tabs_ceiling_temperature_deltaref',
                          'tabs_floor_temperature_delta',
                          'tabs_floor_temperature_deltaref',
                          'tabs_room_temperature_aircenter010',
                          'tabs_room_temperature_aircenter060',
                          'tabs_room_temperature_aircenter110',
                          'tabs_room_temperature_aircenter170',
                          'tabs_room_temperature_aircenter355',
                          'tabs_guard_temperature_airfloor',
                          'tabs_guard_temperature_airceiling',
                          'tabs_guard_temperature_airwallsouth',
                          'tabs_guard_temperature_airwallnorth',
                          'tabs_guard_temperature_airwalleast',
                          'tabs_guard_temperature_airwallwest',
                          
                          ]
        self.multiplex_reader = MultiplexReader(self.codenames)
        self.multiplex_reader.start()
        #omega_temperature.update_values()
        
        time.sleep(3.5)
        
        chlist = Setting_channel_list
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
        while not self.quit and self.multiplex_reader.isAlive():
            try:
                #print(i)
                time.sleep(1)
                for name in self.codenames:
                    v = self.loggers[name].read_value()
                    #livesocket.set_point_now(name, v)
                    self.PullSocket.set_point_now(name, v)
                    #print(i, name, v)
                    if self.loggers[name].read_trigged():
                        if __name__ == '__main__':
                            print('Log: ', i, name, v)
                        #print(name, v)
                        self.db_logger.enqueue_point_now(name, v)
                        self.loggers[name].clear_trigged()
            except (KeyboardInterrupt, SystemExit):
                self.quit = True
                pass
                #self.omega_temperature.close()
                #report error and proceed
            i += 1
    def stop(self):
        self.quit = True
        self.multiplex_reader.stop()
        self.PullSocket.stop()
        self.db_logger.stop()        
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
    #print('END')
    
