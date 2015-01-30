""" Pressure and temperature logger """
# pylint: disable=C0301,R0904, C0103

import threading
import time
import logging
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
fromt PyExpLabSys.drivers.keithley_2700 as keithley2700



if __name__ == '__main__':
    ports = {}
    ports[0] = 'usb-9710_7840-if00-port0'
    ports[1] = 'usb-9710_7840-if00-port1'
    ports[2] = 'usb-9710_7840-if00-port2'
    ports[3] = 'usb-9710_7840-if00-port3'

    dmm = keithley2700('serial', device=ports[0])
    print(dmm.read_software_version())
    while True:
        print(dmm.read_voltage())

