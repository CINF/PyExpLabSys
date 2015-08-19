# -*- coding: utf-8 -*-
"""
Created on Wed Aug 19 16:42:35 2015

@author: pi
"""

import curses
import socket
import threading
import time
import socket
import json

import credentials
import socketinfo
from PyExpLabSys.common.loggers import ContinuousLogger
ContinuousLogger.host = credentials.dbhost
ContinuousLogger.database = credentials.dbname
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger

class CursesTui(threading.Thread):
    """ the display TUI for changing and chowing the temperature of the high
    pressure cell"""
    def __init__(self, codenames):
        threading.Thread.__init__(self)
        self.screen = curses.initscr()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.codenames = codenames
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)
        self.time = time.time()
        self.countdown = False
        self.last_key = None
        self.quit = False
        self.ttl = 50
        self.setpoints = {'tabs_guard_setpoint': 25.0, 'tabs_floor_setpoint': 25.0, 'tabs_ceiling_setpoint': 25.0, 'tabs_cooling_setpoint': 25.0}  
        self.temperatures = {'tabs_guard_temperature': None, 'tabs_floor_temperature': None, 'tabs_ceiling_temperature': None, 'tabs_cooling_temperature': None} 
        
    def value(self, channel):
        """ Read the pressure """
        #self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel == 0:
                return_val = self.setpoints['tabs_guard_setpoint']
            elif channel == 1:
                return_val = self.setpoints['tabs_floor_setpoint']
            elif channel == 2:
                return_val = self.setpoints['tabs_ceiling_setpoint']
            elif channel == 3:
                return_val = self.setpoints['tabs_cooling_setpoint']
        #print('return_val: ', return_val, '<-')
        return return_val
    def update_temperatures(self,):
        info = socketinfo.INFO['tabs_temperatures']
        host_port = (info['host'], info['port'])
        command = 'json_wn'
        self.sock.sendto(command, host_port)
        data = json.loads(self.sock.recv(2048))
        #print(data)
        now = time.time()
        for key, value in data.items():
            co = str(key)
            if now - value[0] > 3*60 or value[1] == 'OLD_DATA': # this is 3min change to 5spowers
                # value to old
               self.temperatures[co] = None
            else:
                self.temperatures[co] = value[1]
        #print(self.temperatures)
        return self.temperatures

    def run(self,):
        while not self.quit:
            time.sleep(0.1)
            self.update_temperatures()
            self.screen.addstr(3, 2, "Tabs controller" )
            try:
                self.screen.addstr(6, 2,
                                   "Setpoint:    {0:+.2f} C".format(
                                       self.setpoints['tabs_guard_setpoint']))
            except Exception as exception:
                global EXCEPTION
                EXCEPTION = exception
            line = 8
            for co in self.codenames:
                try:
                    self.screen.addstr(line, 2,
                                       "Temperature: {0:+.2f} C    {1:+.2f} C".format(
                                           self.temperatures[co[:-8]+'temperature'], self.setpoints[co]))
                except:
                    self.screen.addstr(line, 2,
                                   "Temperature:             {0:+.2f} C".format(
                                       self.setpoints[co]))
                line += 1
            if self.last_key != None:
                self.screen.addstr(24, 2,
                                   " Latest key: {}".format(self.last_key))
            self.screen.addstr(21, 2,
                               "q: quit program, ")
            self.screen.addstr(22, 2,
                               "1: increase, " \
                               "!, decrease, ")
            n = self.screen.getch()
            if n == ord("q"):
                self.quit = True
                self.last_key = chr(n)
            elif n == ord('z'):
                for key, value in self.setpoints.items():
                    self.setpoints[key] += 0.1
                self.last_key = chr(n)
            elif n == ord('x'):
                for key, value in self.setpoints.items():
                    self.setpoints[key] -= 0.1
                self.last_key = chr(n)
            self.screen.refresh()
        time.sleep(5)
        self.stop()
        #print EXCEPTION

    def stop(self):
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()
        
        
if __name__ == '__main__':
    codenames = ['tabs_guard_setpoint',
                 'tabs_floor_setpoint',
                 'tabs_ceiling_setpoint',
                 'tabs_cooling_setpoint',
                 ]
    sockname = 'tabs_setpoints'
    PullSocket = DateDataPullSocket(sockname, codenames, timeouts=[60.0]*len(codenames), port = socketinfo.INFO[sockname]['port'])
    PullSocket.start()
    
    TUI = CursesTui(codenames)
    TUI.start()
    #time.sleep(5)
    
    chlist = {'tabs_guard_setpoint': 0, 'tabs_floor_setpoint': 1, 'tabs_ceiling_setpoint': 2, 'tabs_cooling_setpoint': 3}
    loggers = {}
    for key in codenames:
        loggers[key] = ValueLogger(TUI, comp_val = 1.9, maximumtime=60,
                                        comp_type = 'lin', channel = chlist[key])
        loggers[key].start()
    #livesocket = LiveSocket('tabs_temperature_logger', codenames, 2)
    #livesocket.start()
    
    
    
    #db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=codenames)
    #print('Hostname of db logger: ' + db_logger.host)
    #db_logger.start()
    
    i = 0
    while TUI.isAlive():
        #print(i)
        try:
            #print(i)
            time.sleep(2)
            for name in codenames:
                v = loggers[name].read_value()
                #print('Status: ', name , v)
                #livesocket.set_point_now(name, v)
                PullSocket.set_point_now(name, v)
                if loggers[name].read_trigged():
                    #print('Log: ', name, v)
                    #db_logger.enqueue_point_now(name, v)
                    loggers[name].clear_trigged()
        except (KeyboardInterrupt, SystemExit):
            TUI.stop()
            #report error and proceed
        i += 1
    PullSocket.stop()
    for key in codenames:
        loggers[key].status['quit'] = True
    #print(i)
    print('END')