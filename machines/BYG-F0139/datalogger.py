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
from PyExpLabSys.auxiliary.pid import PID
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
        self.update()
    def run(self):
        self.update_temperatures()
        self.update_flows
#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)


OmegaPortsDict = {}
#OmegaPortsDict['omega ceiling'] = '/dev/serial/by-id/usb-FTDI_USB-RS_Cable_FTWEA5HJ-if00-port0'
OmegaPortsDict['omega floor'] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTYIWHC9-if00-port0'
OmegaPortsDict['omega guard'] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWEA5HJ-if00-port0'
OmegaPortsDict['omega cooling'] = '/dev/serial/by-id/usb-OMEGA_ENGINEERING_12.34-if00'

OmegaCommStnd = {}
#OmegaCommStnd['omega ceiling'] = 'rs232'
OmegaCommStnd['omega floor'] = 'rs485' #add 2
OmegaCommStnd['omega guard'] = 'rs485'
OmegaCommStnd['omega cooling'] = 'rs232'

OmegaCommAdd = {}
OmegaCommAdd['omega floor'] = 1
OmegaCommAdd['omega guard'] = 1

OmegaDict = {}
for key in OmegaPortsDict.keys():
    OmegaDict[key] = omega_CNi32.ISeries(OmegaPortsDict[key], 9600, comm_stnd=OmegaCommStnd[key])

test = 'omega floor'
#id_ = OmegaDict['omega floor'].command('R21', address=2)
OmegaDict[test].command('X01', address=1)

OmegaDict[test].command('R08', address=1)
OmegaDict[test].command('W0882', address=1)
OmegaDict[test].command('Z02', address = 1)

time.sleep(5)
OmegaDict[test].command('R08', address=1)
OmegaDict[test].command('X01', address=1)

"""
for key, value in OmegaDict.items():
    print("Omega: {}".format(key))
    if OmegaCommStnd[key] == 'rs485':
        print('Temp: ' + str(value.read_temperature(address=OmegaCommAdd[key]) ) )
        print('Format: ' + str(value.command('R08', address=OmegaCommAdd[key]) ) )
    else:
        print('Temp: ' + str(value.read_temperature() ) )
        print('Format: ' + str(value.command('R08') ) )
"""
for om in OmegaDict.values():
    om.close()
