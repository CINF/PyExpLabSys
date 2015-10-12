# -*- coding: utf-8 -*-
""" Omega CN7800 Modbus driver. Might also work with other CN units
"""

import logging
import serial
import minimalmodbus

LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
#LOGGER.addHandler(logging.NullHandler())
LOGGER.addHandler(logging.StreamHandler())

class CN7800(object):
    """Driver for the omega CN7800"""

    def __init__(self, port):
        self.comm = minimalmodbus.Instrument(port, 1)
        self.comm.serial.baudrate = 9600
        self.comm.serial.parity = serial.PARITY_EVEN
        self.comm.serial.timeout = 0.5
        self.temperature = self.comm.read_register(4096, 1)


    def read_temperature(self):
        """ Read the temperature from the device """
        self.temperature = self.comm.read_register(4096, 1)
        return self.temperature
