# -*- coding: utf-8 -*-

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
        self.SYSTEMS = {}
        for sy in ['tabs_guard', 'tabs_floor', 'tabs_ceiling', 'tabs_cooling', 'tabs_ice']:
            self.SYSTEMS[sy] = {'temperature_inlet': None, # float in C
                                'temperature_outlet': None, # float in C
                                'temperature_setpoint': None, # float in C
                                'valve_cooling': None, # float 0-1
                                'valve_heating': None, # float 0-1
                                'pid_value': None, # float -1-1
                                'water_flow': None} # float in l/min
        for sy, value in self.SYSTEMS.items():
            value['temperature_setpoint'] = 25.0
        #self.setpoints = {'tabs_guard_setpoint': 25.0, 'tabs_floor_setpoint': 25.0, 'tabs_ceiling_setpoint': 25.0, 'tabs_cooling_setpoint': 25.0}  
        #self.temperatures = {'tabs_guard_temperature': None, 'tabs_floor_temperature': None, 'tabs_ceiling_temperature': None, 'tabs_cooling_temperature': None} 
        
    def value(self, channel):
        """ Read the present values, temperature setpoint
        this function is used in connection with the logger module"""
        #self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            me = 'temperature_setpoint'
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
        #print('return_val: ', return_val, '<-')
        return return_val

    def update_temperatures(self,):
        """ Read the temperature from a external socket server"""
        info = socketinfo.INFO['tabs_temperatures']
        host_port = (info['host'], info['port'])
        command = 'json_wn'
        self.sock.sendto(command, host_port)
        data = json.loads(self.sock.recv(2048))
        now = time.time()
        #print(data)
        for key, value in data.items():
            _key = str(key).rsplit('_')
            sy = _key[0]+'_' + _key[1]
            me = _key[2]+'_' + _key[3]
            try:
                if abs(now - value[0]) > 3*60 or value[1] == 'OLD_DATA': # this is 3min change to 5s
                    # value to old
                   #self.pidvalues[co] = 0.0
                   self.SYSTEMS[sy][me] = None
                else:
                    self.SYSTEMS[sy][me] = value[1]
            except:
                self.SYSTEMS[sy][me] = None
        #print(self.temperatures)
        return self.SYSTEMS

    def run(self,):
        while not self.quit:
            time.sleep(0.1)
            self.update_temperatures()
            self.screen.addstr(3, 2, "Tabs controller" )
            try:
                self.screen.addstr(6, 2,
                                   "Setpoint:    {0:+.2f} C".format(
                                       self.SYSTEMS['tabs_guard']['temperature_setpoint']))
            except Exception as exception:
                global EXCEPTION
                EXCEPTION = exception
            line = 8
            self.screen.addstr(line, 2, "{0:15} {1:2} {2:2}".format('System', 'Temperature', 'Setpoint'))
            line += 1
            for sy in ['tabs_guard', 'tabs_floor', 'tabs_ceiling', 'tabs_cooling', 'tabs_ice']:#self.SYSTEMS.keys():
                try:
                    self.screen.addstr(line, 2,
                                       "{0:15}: {1:+.2f} C    {2:+.2f} C".format(
                                       sy,
                                       self.SYSTEMS[sy]['temperature_inlet'],
                                       self.SYSTEMS[sy]['temperature_setpoint']))
                except:
                    self.screen.addstr(line, 2,
                                       "{0:15}:             {1:+.2f} C".format(
                                       sy,
                                       self.SYSTEMS[sy]['temperature_setpoint']))
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
                for key, value in self.SYSTEMS.items():
                    value['temperature_setpoint'] += 0.1
                self.last_key = chr(n)
            elif n == ord('x'):
                for key, value in self.SYSTEMS.items():
                    value['temperature_setpoint'] -= 0.1
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
        
        
class MainTui(threading.Thread):
    """ Temperature reader """
    def __init__(self,):
        threading.Thread.__init__(self)
        from mytui import CursesTui
        self.quit = False
        self.codenames = ['tabs_guard_temperature_setpoint',
                     'tabs_floor_temperature_setpoint',
                     'tabs_ceiling_temperature_setpoint',
                     'tabs_cooling_temperature_setpoint',
                     ]
        sockname = 'tabs_setpoints'
        self.PullSocket = DateDataPullSocket(sockname, self.codenames, timeouts=[60.0]*len(self.codenames), port = socketinfo.INFO[sockname]['port'])
        self.PullSocket.start()
        
        self.TUI = CursesTui(codenames)
        self.TUI.start()
        #time.sleep(5)
        
        chlist = {'tabs_guard_temperature_setpoint': 0, 'tabs_floor_temperature_setpoint': 1, 'tabs_ceiling_temperature_setpoint': 2, 'tabs_cooling_temperature_setpoint': 3}
        self.loggers = {}
        for key in self.codenames:
            self.loggers[key] = ValueLogger(self.TUI, comp_val = 0.2, maximumtime=60,
                                            comp_type = 'lin', channel = chlist[key])
            self.loggers[key].start()
        #livesocket = LiveSocket('tabs_temperature_logger', codenames, 2)
        #livesocket.start()
        
        
        
        self.db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=self.codenames)
        #print('Hostname of db logger: ' + db_logger.host)
        self.db_logger.start()
    
    def run(self):
        i = 0
        while not self.quit:
            #print(i)
            try:
                #print(i)
                time.sleep(2)
                for name in self.codenames:
                    v = self.loggers[name].read_value()
                    #print('Status: ', name , v)
                    #livesocket.set_point_now(name, v)
                    self.PullSocket.set_point_now(name, v)
                    if self.loggers[name].read_trigged():
                        #print('Log: ', name, v)
                        self.db_logger.enqueue_point_now(name, v)
                        self.loggers[name].clear_trigged()
            except (KeyboardInterrupt, SystemExit):
                self.TUI.stop()
                #report error and proceed
            i += 1

    def stop(self):
        self.quit = True
        self.PullSocket.stop()
        for key in self.codenames:
            self.loggers[key].status['quit'] = True
        
        
if __name__ == '__main__':
    codenames = ['tabs_guard_temperature_setpoint',
                 'tabs_floor_temperature_setpoint',
                 'tabs_ceiling_temperature_setpoint',
                 'tabs_cooling_temperature_setpoint',
                 ]
    sockname = 'tabs_setpoints'
    PullSocket = DateDataPullSocket(sockname, codenames, timeouts=[60.0]*len(codenames), port = socketinfo.INFO[sockname]['port'])
    PullSocket.start()
    
    TUI = CursesTui(codenames)
    TUI.start()
    #time.sleep(5)
    
    chlist = {'tabs_guard_temperature_setpoint': 0, 'tabs_floor_temperature_setpoint': 1, 'tabs_ceiling_temperature_setpoint': 2, 'tabs_cooling_temperature_setpoint': 3}
    loggers = {}
    for key in codenames:
        loggers[key] = ValueLogger(TUI, comp_val = 0.2, maximumtime=60,
                                        comp_type = 'lin', channel = chlist[key])
        loggers[key].start()
    #livesocket = LiveSocket('tabs_temperature_logger', codenames, 2)
    #livesocket.start()
    
    
    
    db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=codenames)
    #print('Hostname of db logger: ' + db_logger.host)
    db_logger.start()
    
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
                    db_logger.enqueue_point_now(name, v)
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
