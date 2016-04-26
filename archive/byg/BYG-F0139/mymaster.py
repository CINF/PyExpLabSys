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
    MDL.daemon = True
    MDL.start()
    #time.sleep(4)
    
    from mymultiplexer import MainMultilogger
    MML = MainMultilogger()
    MML.daemon = True
    MML.start()
    #time.sleep(4)
    
    from mytui import MainTui
    MT = MainTui()
    MT.start()
    time.sleep(4)
    
    from mypid import MainPID
    MP = MainPID()
    MP.daemon = True
    MP.start()
    time.sleep(4)
    
    from mydigitalinout import MainDGIO
    DGIO = MainDGIO()
    DGIO.daemon = True
    DGIO.start()
    
    while MT.isAlive():
        try:
            time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            MT.quit = True
    DGIO.quit = True
    MP.quit = True
    MT.quit = True
    MML.quit = True
    MDL.quit = True
    print('END')
    
    
