# -*- coding: utf-8 -*-
# !/usr/bin/env python
# pylint: disable=C0301,R0904, C0103
""" Pressure and temperature logger """

from __future__ import print_function

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
from PyExpLabSys.auxiliary.pic import pid
#import PyExpLabSys.drivers.omegabus as omegabus
import PyExpLabSys.drivers.omega_cni as omega_CNi32
#import PyExpLabSys.drivers.kampstrup as kampstrup
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
            self.temperature = self.omega.read_temperature(address = 2)

class TABS(threading.Thread):
    """ class for control of the TABS test room """
    def __init__(self, Multical, Omegas):
        threading.Thread.__init__(self)
        self.Multical = Multical
        self.Omegas = Omegas
        self.temperatures
    def  update_temperatures(self,):
        self.
    def run(self):
        self.update_temperatures()
        self.update_flows
#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)

ports = {}
ports['Omega ceil'] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWEA5HJ-if00-port0'
ports['Kamp ceil'] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTYIWHC9-if00-port0'
Omega = {}
Omega['a'] = omega_CNi32.ISeries(ports['Omega ceil'], 9600, comm_stnd='rs485')



for i in range(5):
    print('address: ' + str(i) + ' ' + str(temp.read_temperature(address=i) ) )


temp.close()
