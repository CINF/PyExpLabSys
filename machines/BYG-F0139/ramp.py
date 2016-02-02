# -*- coding: utf-8 -*-
"""
Created on Tue Oct 21 08:49:40 2014

@author: aufn
"""

# Important dont change the import statements
import time
import numpy as np
import socket
import json

import sys
sys.path.insert(1, '/home/pi/PyExpLabSys')

import logging
import credentials
import socketinfo

logging.basicConfig(filename="logger_ramp.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

class ramp(object):
    """ class for automatically control the setpoints"""
    def __init__(self,):
        logging.info('Ramp class started')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(3)
        
        date_str = "2015-12-06 16:37:00" # <---- startdate for experiment, change HERE
        time_tuple = time.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        start = time.mktime(time_tuple)
        #start = time.time()
        self.start_time = start
        
        date_str = "2016-12-30 18:00:00" # <---- enddate for experiment, change HERE
        time_tuple = time.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        end = time.mktime(time_tuple)
        #end = self.start_time + 3600*3
        self.end_time = end
        self.setpoint = self.standard()
        #time.mktime(time.strptime("2015-10-30 13:30:00", "%Y-%m-%d %H:%M:%S"))
        
    def present(self):
        self.update_temperatures()
        t0 = time.time()
        if t0 < self.start_time: # before start of experiment, set safe conditions
            self.setpoint = {
                        'tabs_guard_temperature_setpoint': 15.0,
                        'tabs_floor_temperature_setpoint': 15.0,
                        'tabs_ceiling_temperature_setpoint': 15.0,
                        'tabs_cooling_temperature_setpoint': 30.0,
                     }
        elif self.start_time < t0 < self.end_time: # <---- setpoint during the experiment, change below
            if self.temp['tabs_room_temperature_control'] == None:
                self.temp['tabs_room_temperature_control'] = self.standard()['tabs_guard_temperature_setpoint']
            
            self.setpoint = {
                        'tabs_guard_temperature_setpoint': self.temp['tabs_room_temperature_control'],
                        'tabs_floor_temperature_setpoint': 15.0,
                        'tabs_ceiling_temperature_setpoint': 15.0,
                        'tabs_cooling_temperature_setpoint': 15.0 - 2.0,
                     }
        elif self.end_time < t0: # after end of experiment, set safe conditions
            self.setpoint = {
                        'tabs_guard_temperature_setpoint': 22.0,
                        'tabs_floor_temperature_setpoint': 15.0,
                        'tabs_ceiling_temperature_setpoint': 15.0,
                        'tabs_cooling_temperature_setpoint': 30.0,
                     }
        return self.setpoint
    def standard(self,):
        self.setpoint = {
                        'tabs_guard_temperature_setpoint': 15.0,
                        'tabs_floor_temperature_setpoint': 15.0,
                        'tabs_ceiling_temperature_setpoint': 15.0,
                        'tabs_cooling_temperature_setpoint': 30.0,
                     }
        return self.setpoint
        
    def update_temperatures(self,):
        if __name__ == '__main__':
            print('Updating ramp')
        """ Read the temperature from a external socket server"""
        self.temp = {}
        try:
            info = socketinfo.INFO['tabs_temperatures']
            host_port = (info['host'], info['port'])
            command = 'json_wn'
            self.sock.sendto(command, host_port)
            data = json.loads(self.sock.recv(2*2048))
            now = time.time()
            for key, value in data.items():
                try:
                    if abs(now - value[0]) > 3*60 or value[1] == 'OLD_DATA': # this is 3min change to 5s
                        pass
                    else:
                        logging.warn('Data is old')
                        self.temp[key] = value[1]
                except:
                    logging.warn('Could not calculate time difference')
        except socket.timeout:
            logging.warn('Socket has timeout')
        if not 'tabs_room_temperature_control' in self.temp.keys():
            self.temp['tabs_room_temperature_control'] = self.standard()['tabs_guard_temperature_setpoint']
            
        return self.temp

if __name__ == '__main__':
    R = ramp()
    for k, v in R.present().items():
        print(k, v)

