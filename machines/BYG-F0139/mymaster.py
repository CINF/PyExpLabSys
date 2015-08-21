# -*- coding: utf-8 -*-

#import curses
#import socket
import threading
import time
#import socket
#import json

import credentials
import socketinfo
from PyExpLabSys.common.loggers import ContinuousLogger
ContinuousLogger.host = credentials.dbhost
ContinuousLogger.database = credentials.dbname
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger






class MainDatalogger(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        threading.Thread.__init__(self)
        from datalogger import TemperatureReader
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
        
        self.db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=codenames)
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
                    if self.loggers[name].read_trigged():
                        #print(i, name, v)
                        self.db_logger.enqueue_point_now(name, v)
                        self.loggers[name].clear_trigged()
            except (KeyboardInterrupt, SystemExit):
                self.omega_temperature.close()
                #report error and proceed
            i += 1
    def stop(self):
        self.quit = True
        self.PullSocket.close()
        for key in self.codenames:
            self.loggers[key].status['quit'] = True
            
            
class MainTui(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
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
            
            
class MainPID(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        threading.Thread.__init__(self)
        from mypid import PidTemperatureControl
        self.quit = False
        self.codenames = ['tabs_guard_pid_value',
                     'tabs_floor_pid_value',
                     'tabs_ceiling_pid_value',
                     'tabs_cooling_pid_value',
                     ]
        sockname = 'tabs_pids'
        self.PullSocket = DateDataPullSocket(sockname, self.codenames, timeouts=[60.0]*len(self.codenames), port = socketinfo.INFO[sockname]['port'])
        self.PullSocket.start()
        
        self.PTC = PidTemperatureControl(self.codenames)
        self.PTC.start()
        #time.sleep(5)
        
        chlist = {'tabs_guard_pid_value': 0, 'tabs_floor_pid_value': 1, 'tabs_ceiling_pid_value': 2, 'tabs_cooling_pid_value': 3}
        self.loggers = {}
        for key in self.codenames:
            self.loggers[key] = ValueLogger(self.PTC, comp_val = 0.10, maximumtime=60,
                                            comp_type = 'lin', channel = chlist[key])
            self.loggers[key].start()
        #livesocket = LiveSocket('tabs_temperature_logger', codenames, 2)
        #livesocket.start()
    
        
        self.db_logger = ContinuousLogger(table='dateplots_tabs', username=credentials.user, password=credentials.passwd, measurement_codenames=codenames)
        #print('Hostname of db logger: ' + self.db_logger.host)
        self.db_logger.start()
    def run(self,):
        i = 0
        while not self.quit:
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
                self.PTC.stop()
                #report error and proceed
            i += 1
    def stop(self):
        self.quit = True
        self.PullSocket.stop()
        for key in self.codenames:
            self.loggers[key].status['quit'] = True


class MainDGIO(threading.Thread):
    """ Temperature reader """
    def __init__(self, codenames):
        threading.Thread.__init__(self)
        from digitalinot import ValveControl
        self.quit = False
        self.codenames = ['tabs_guard_valve_heating',
                     'tabs_floor_valve_heating',
                     'tabs_ceiling_valve_heating',
                     'tabs_cooling_valve_heating',
                     ]
        sockname = 'tabs_valve'
        #codenames = socketinfo.INFO[sockname]['codenames']
        self.PullSocket = DateDataPullSocket(sockname, self.codenames, timeouts=[60.0]*len(self.codenames), port = socketinfo.INFO[sockname]['port'])
        self.PullSocket.start()
        self.VC = ValveControl(self.codenames)
        self.VC.start()
        chlist = {'tabs_guard_valve_heating': 0, 'tabs_floor_valve_heating': 1, 'tabs_ceiling_valve_heating': 2, 'tabs_cooling_valve_heating': 3}
        self.loggers = {}
        for key in self.codenames:
            self.loggers[key] = ValueLogger(self.VC, comp_val = 1.9, maximumtime=60, comp_type = 'lin', channel = chlist[key])
            self.loggers[key].start()
    def run(self,):
        i = 0
        while not self.quit:
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
                        #db_logger.enqueue_point_now(name, v)
                        self.loggers[name].clear_trigged()
            except (KeyboardInterrupt, SystemExit):
                self.VC.stop()
                #report error and proceed
            i += 1
    def stop(self):
        self.quit = True
        self.PullSocket.stop()
        for key in self.codenames:
            self.loggers[key].status['quit'] = True




if __name__ == '__main__':
    MDL = MainDatalogger()
    MDL.start()
    time.sleep(2)
    MT = MainTui()
    MT.start()
    time.sleep(2)
    MP = MainPID()
    MP.start()
    time.sleep(2)
    DGIO = MainDGIO()
    DGIO.start()
    
    while MDL.isAlive():
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            DGIO.stop()
            MP.stop()
            MT.stop()
            MDL.stop()
    print('END')
    
