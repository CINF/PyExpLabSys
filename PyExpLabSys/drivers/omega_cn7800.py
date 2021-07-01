# -*- coding: utf-8 -*-
""" Omega CN7800 Modbus driver. Might also work with other CN units. Settings
on the device should be RTU and datalength 8 bit.
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
        self.comm = minimalmodbus.Instrument("/dev/serial/by-id/" + port, 1)
        self.comm.serial.baudrate = 9600
        self.comm.serial.parity = serial.PARITY_EVEN
        self.comm.serial.timeout = 0.5
        self.temperature = -999


    def read_temperature(self):
        """ Read the temperature from the device """
        self.temperature = self.comm.read_register(0x1000, 1)
        return self.temperature
    
    def read_setpoint(self):
        """ Read the temperature setpoint """
        setpoint = self.comm.read_register(0x1001,1)
        return setpoint

    def write_setpoint(self, new_setpoint):
        """ Write a new setpoint to the device """
        self.comm.write_register(0x1001,new_setpoint,1)

def main():

    port = "usb-FTDI_USB-RS485_Cable_FT1F9WC2-if00-port0"
#    port = "/dev/ttyUSB0"
    omega = CN7800(port)
    print("Temperature is:", omega.read_temperature())
    print("Set point is:", omega.read_setpoint())
    print("Temperature type is:", type(omega.read_temperature()))
    print("Set point is:", omega.write_setpoint(float(30)))
    print("Set point is:", omega.read_setpoint())
if __name__ == "__main__":
    # Execute only if run as script
    main()
    
