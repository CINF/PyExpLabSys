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

logging.basicConfig(filename="logger_mymultiplexer.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

# this list consist of codenames for a measurement, and the channel number on the multiplxer
Setting_channel_list = {'tabs_ceiling_thermopile_supplyreturn_x02': 101, # DT_up101
                  'tabs_ceiling_temperature_supply_x03': 102, # Tref_up102
                  'tabs_floor_thermopile_supplyreturn_x05': 103, # DT_low103
                  'tabs_floor_temperature_supply_x06': 104, # Tref_low104
                  'tabs_ceiling_temperature_pipesurface_x07': 105, # Tpipe_up
                  'tabs_room_temperature_aircenter110': 106, # 
                  'tabs_ceiling_temperature_pipebetween_x12': 107, # Tceil2_1up
                  'tabs_ceiling_temperature_surfaceupper_x13': 108, # Tconcsus_1up
                  'tabs_ceiling_thermopile_raisedfloor_x14': 109, # DT_1up109
                  'tabs_ceiling_temperature_raisedfloor_x15': 110, # Tsurref_1up
                  'tabs_room_temperature_aircenter010': 111,
                  'tabs_ceiling_thermopile_raisedfloor_x18': 112, # DT_2up112
                  'tabs_ceiling_temperature_raisedfloor_x19': 113, # Tsurref_2up
                  'tabs_ceiling_thermopile_raisedfloor_x20': 114, # DTfloor1_up
                  'tabs_ceiling_temperature_raisedfloor_x21': 115, # Tref1_up
                  'tabs_floor_temperature_pipesurface_x22': 116, # Tpipe_low
                  'tabs_floor_thermopile_raisedfloor_x27': 117, # DT_1flow117
                  'tabs_floor_temperature_raisedfloor_x28': 118, # Tsurref_1low
                  'tabs_floor_thermopile_raisedfloor_x30': 119, # DT_2low119
                  'tabs_floor_temperature_raisedfloor_x31': 120, # Tsurref_2low
                  #'None': 121, # Flow_up121
                  #'None': 122, # Flow_low122
                  
                  #'None': 201
                  'tabs_room_temperature_operative110': 202, # Top2_room_1.1m
                  'tabs_room_temperature_surface_panelupper': 203,
                  'tabs_room_temperature_surfacewallnorth': 204, # Tsur2_room_wall2
                  'tabs_room_temperature_aircenter170': 205, # Tair4_room_1.7m
                  'tabs_room_temperature_aircenter060': 206, # Tair2_room_0.6m
                  'tabs_room_temperature_surface_wallsouth': 207, # Tsur1_room_wall1
                  'tabs_room_temperature_surface_ceilingcenter': 208, # Tsur4_room_ceiling1
                  'tabs_ventilation_temperature_inlet': 209,
                  'tabs_ventilation_temperature_outlet': 210,
                  'tabs_room_temperature_surface_ceilingnearjunction': 211, # Tsur5_room_ceiling2
                  #'None': 212,
                  'tabs_room_temperature_air345': 213, # air_room_0.1mTOP
                  'tabs_room_temperature_surface_floorcenter': 214, # Tsur3_room_floor
                  'tabs_room_temperature_operative060': 215, # Top1_room_0.6
                  #'tabs_room_temperature_surface_ceilingjunction': 216, # Tsur6_room_ceiling3
                  'tabs_room_heatflow_floorcenter': 217, # HeatFlow4_floor
                  'tabs_floor_thermopile_raisedfloor_x32': 218, # DTfloor1_low
                  'tabs_floor_temperature_raisedfloor_x33': 219, # Tref1_low
                  'tabs_room_heatflow_ceilingnearjunction': 220, # HeatFlow3_ceiling
                  #'None': 221,
                  #'None': 222,
                  'tabs_guard_temperature_airfloor_x51': 301, # Tair1_guard
                  'tabs_guard_temperature_airceiling_x50': 302, # Tair2_guard
                  'tabs_guard_temperature_airwallsouth_x52': 303, # Tair3_guard
                  'tabs_guard_temperature_airwallnorth_x53': 304, # Tair4_guard
                  'tabs_guard_temperature_airwalleast_x54': 305, # Tair5_guard
                  'tabs_guard_temperature_airwallwest_x55': 306, # Tair6_guard
                  'tabs_wallsouth_thermopile_roomguard_x56': 307, # DTwall1307
                  'tabs_room_heatflow_ceilingjunction': 308, # HeatFlow2_ceiling
                  'tabs_wallnorth_thermopile_roomguard_x58': 309, # DTwall2309
                  'tabs_wallnorth_temperature_center_x59': 310, # Twallref2
                  'tabs_walleast_thermopile_roomguard_x60': 311, # DTwall3311
                  'tabs_walleast_temperature_center_x61': 312, # Twallref3
                  'tabs_wallwest_thermopile_roomguard_x62': 313, # DTwall4313
                  'tabs_wallwest_temperature_center_x63': 314, # Twallref4
                  'tabs_ceiling_thermopile_sidedeckguard_x64': 315, # DTlen_gaurdup
                  'tabs_ceiling_temperature_sidedeck_x65': 316, # Treflen_guardup
                  'tabs_ceiling_temperature_sidedeck_x66': 317, # Treflen_guardup1
                  'tabs_ceiling_temperature_sidedeck_x67': 318, # Treflen_guardup2
                  #'None': 319,
                  'tabs_room_heatflow_ceilingcenter': 320, # HeatFlow1_ceiling
                  #'None': 321,
                  #'None': 322,
                  }
convertor_channel_list = Setting_channel_list.copy()
for key in convertor_channel_list.keys():
    convertor_channel_list[key] = lambda x: x
    
convertor_channel_list['tabs_room_heatflow_floorcenter'] = lambda x: (x * 10**6 * 3.1546)/0.18
convertor_channel_list['tabs_room_heatflow_ceilingnearjunction'] = lambda x: (x * 10**6 * 3.1546)/0.18
convertor_channel_list['tabs_room_heatflow_ceilingjunction'] = lambda x: (x * 10**6 * 3.1546)/0.18
convertor_channel_list['tabs_room_heatflow_ceilingcenter'] = lambda x: (x * 10**6 * 3.1546)/0.17

class MultiplexReader(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        logging.info('MultiplexReader class started')
        self.codenames = codenames
        threading.Thread.__init__(self)
        port = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
        self.Agilent = Agilent.Agilent34970ADriver(port = port)
        self.DATA = {}
        for key in self.codenames:
            self.DATA[key] = None
        self.chnumbers = self.Agilent.read_scan_list()
        self.named_channel_list = Setting_channel_list
        self.quit = False
        self.ttl = 1000

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
            #print(response)
            chs = response[2::4]
            #print(chs)
            values = response[0::4]
            #print(values)
            self.ttl = 1000
        except:
            logging.warn('Connection error to agilent')
            response = None
        if response != None:
            for ch, value in zip(chs, values):
                #print(ch, value)
                if ch in self.named_channel_list.values():
                    for codename, v in self.named_channel_list.items():
                        if ch == v:
                            self.DATA[codename] = convertor_channel_list[codename](value)
                            break
        return None

    def run(self):
        while not self.quit:            
            self.update_values()
            time.sleep(60)
            
    def stop(self,):
        self.quit = True
        self.Agilent.close()


#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)


class MainMultilogger(threading.Thread):
    """ Temperature reader """
    def __init__(self,):
        logging.info('MainMultilogger class started')
        threading.Thread.__init__(self)
        #from datalogger import TemperatureReader
        self.quit = False
        self.codenames = Setting_channel_list.keys()
        """['tabs_ceiling_temperature_delta',
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
                          
                          ]"""
        self.multiplex_reader = MultiplexReader(self.codenames)
        self.multiplex_reader.daemon = True
        self.multiplex_reader.start()
        #omega_temperature.update_values()
        
        time.sleep(3.5)
        
        chlist = Setting_channel_list
        self.loggers = {}
        for key in self.codenames:
            self.loggers[key] = ValueLogger(self.multiplex_reader, comp_val = 0.5, maximumtime=300,
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
                    if self.loggers[name].read_trigged() and abs(v) < 9.9E+5 and v != None:
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
        self.stop()
        
    def stop(self):
        self.quit = True
        self.multiplex_reader.stop()
        self.PullSocket.stop()
        self.db_logger.stop()        
        for key in self.codenames:
            self.loggers[key].status['quit'] = True

if __name__ == '__main__':
    MML = MainMultilogger()
    time.sleep(5)
    MML.start()
    
    while MML.isAlive():
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            MML.quit = True
    #print('END')
    
