# -*- coding: utf-8 -*-

from __future__ import print_function, division
#import curses
#import socket
import threading
import time
#import socket
#import json


import sys
sys.path.insert(1, '/home/pi/PyExpLabSys')

#import credentials
#import socketinfo
#from PyExpLabSys.common.loggers import ContinuousLogger
#ContinuousLogger.host = credentials.dbhost
#ContinuousLogger.database = credentials.dbname
#from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.value_logger import ValueLogger




if __name__ == '__main__':
    
    from mydatalogger import MainDatalogger
    MDL = MainDatalogger()
    MDL.start()
    #time.sleep(4)
    
    from mymultiplexer import MainMultilogger
    MML = MainMultilogger()
    MML.start()
    #time.sleep(4)
    
    from mytui import MainTui
    MT = MainTui()
    MT.start()
    time.sleep(4)
    
    from mypid import MainPID
    MP = MainPID()
    MP.start()
    time.sleep(4)
    
    from mydigitalinout import MainDGIO
    DGIO = MainDGIO()
    DGIO.start()
    
    while MT.isAlive():
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            MT.stop()
    DGIO.stop()
    MP.stop()
    MT.stop()
    MML.stop()
    MDL.stop()
    print('END')
    
    
