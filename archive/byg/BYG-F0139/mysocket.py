# -*- coding: utf-8 -*-
# !/usr/bin/env python
# pylint: disable=C0301,R0904, C0103
""" Pressure and temperature logger """

from __future__ import print_function

#import curses
import socket
import threading
import time
import socket
import json

import sys
sys.path.insert(1, '/home/pi/PyExpLabSys')

import credentials
import socketinfo
#from PyExpLabSys.common.loggers import ContinuousLogger
#ContinuousLogger.host = credentials.dbhost
#ContinuousLogger.database = credentials.dbname
from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.value_logger import ValueLogger


class MySocket(threading.Thread):
    """ Temperature reader """
    def __init__(self):
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2)
        self.quit = False
        sockname = 'tabs_all'
        self.codenames = socketinfo.INFO[sockname]['codenames']
        self.PullSocket = DateDataPullSocket(sockname, self.codenames, timeouts=[60.0]*len(self.codenames), port = socketinfo.INFO[sockname]['port'])
        self.PullSocket.start()
        self.data = {}
        for co in self.codenames:
            self.data[co] = None
        
    def run(self,):
        i = 0
        while not self.quit:
            try:
                #print(i)
                time.sleep(2)
                for name in self.codenames:
                    v = self.loggers[name].read_value()
                    v = self.data[name]
                    self.PullSocket.set_point_now(name, v)
            except (KeyboardInterrupt, SystemExit):
                pass
                #self.VC.stop()
                #report error and proceed
            i += 1
    def update_values(self,):
        """ Read the temperature from a external socket server"""
        for so in ['tabs_temperatures', 'tabs_setpoints', 'tabs_pids', 'tabs_valve', 'tabs_multiplexer']:
            try:
                info = socketinfo.INFO[so]
                host_port = (info['host'], info['port'])
                command = 'json_wn'
                self.sock.sendto(command, host_port)
                data = json.loads(self.sock.recv(2048))
                now = time.time()
                #print(data)
                for key, value in data.items():
                    try:
                        if abs(now - value[0]) > 3*60 or value[1] == 'OLD_DATA': # this is 3min change to 5s
                           self.data[key] = None
                        else:
                            self.data[key] = value[1]
                    except:
                        self.data[key] = None
            except socket.timeout:
                pass
        return self.data
    def stop(self):
        self.quit = True
        self.PullSocket.stop()

if __name__ == '__main__':
    MSo = MySocket()
    MSo.start()
    
    while MSo.isAlive():
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            MSo.stop()
    print('END')


    
    