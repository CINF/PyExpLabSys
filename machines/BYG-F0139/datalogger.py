# -*- coding: utf-8 -*-
# !/usr/bin/env python
# pylint: disable=C0301,R0904, C0103
""" Pressure and temperature logger """

import sys
sys.path.insert(1, '/home/pi/PyExpLabsys')
sys.path.insert(2, '../..')

import threading
import time
import logging
#from PyExpLabSys.common.loggers import ContinuousLogger
#from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.sockets import LiveSocket
#from PyExpLabSys.common.value_logger import ValueLogger
#import PyExpLabSys.drivers.omegabus as omegabus
import PyExpLabSys.drivers.omega_cni as omega_CNi32
#import credentials

#==============================================================================
# class OldTempReader(threading.Thread):
#     """ Temperature reader """
#     def __init__(self, omegabus):
#         threading.Thread.__init__(self)
#         self.omegabus = omegabus
#         self.ttl = 20
#         self.temperature = None
#         self.quit = False
# 
#     def value(self):
#         """ Read the temperaure """
#         self.ttl = self.ttl - 1
#         if self.ttl < 0:
#             self.quit = True
#         return(self.temperature)
# 
#     def run(self):
#         while not self.quit:
#             self.ttl = 20
#             time.sleep(1)
#             self.temperature = self.omegabus.ReadValue(2)
#==============================================================================


class NGTempReader(threading.Thread):
    """ Temperature reader """
    def __init__(self, omega):
        threading.Thread.__init__(self)
        self.omega = omega
        self.ttl = 20
        self.temperature = None
        self.quit = False

    def value(self):
        """ Read the temperaure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        return(self.temperature)

    def run(self):
        while not self.quit:
            self.ttl = 20
            time.sleep(1)
            self.temperature = self.omega.read_temperature()

#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)

port = '/dev/serial/by-id/' + 'usb-FTDI_USB-RS232_Cable_FTWR5F6W-if00-port0'
ng_temp = omega_CNi32.ISeries(port, 9600)
print(ng_temp.command('R01'))
