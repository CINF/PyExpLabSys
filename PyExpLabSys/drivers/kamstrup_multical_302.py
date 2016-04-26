# -*- coding: utf-8 -*-
#!/usr/bin/env python

""" Kamstrup Multical 302 Modbus driver.
"""

import logging
import serial
import minimalmodbus

LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
#LOGGER.addHandler(logging.NullHandler())
LOGGER.addHandler(logging.StreamHandler())

class Multical302(object):
    """Driver for the Kamstrup Multical 302"""

    def __init__(self, port):
        self.comm = minimalmodbus.Instrument(port, 14)#, minimalmodbus.MODE_ASCII)
        self.comm.serial.baudrate = 2400
        self.comm.serial.parity = serial.PARITY_NONE#EVEN
        self.comm.serial.timeout = 0.5
        self.register_ids = {'Date': 1003,
                             'Clock': 1002,
                             'InfoCode': 99,
                             'InfoEventCounter': 113,
                             'HourCounter': 1004,
                             'Energy1': 60,
                             'Energy3': 63,
                             'Energy8': 97,
                             'Energy9': 110,
                             'Volume1': 68,
                             'Temp1': 86,
                             'Temp2': 87,
                             'Temp1-Temp2': 89,
                             'Flow1': 74,
                             'Power1': 80,
                             'V1HighRes': 239,
                             'E1HighRes': 266,
                             'E3HighRes': 267,
                             'LogDaySetUp': 98,
                             'AvrTemp1(y)': 146,
                             'AvrTemp2(y)': 147,
                             'AvrTemp1(m)': 149,
                             'AvrTemp2(m)': 150,
                             'AutoIntT1Averrage': 229,
                             'AutoIntT2Averrage': 230,
                             'MaxFlow1Date(y)': 123,
                             'MaxFlow1(y)': 124,
                             'MaxPower1Date(y)': 127,
                             'MaxPower1(y)': 128,
                             'MaxFlow1Date(m)': 138,
                             'MaxFlow1(m)': 139,
                             'MaxPower1Date(m)': 142,
                             'MaxPower1(m)': 143,
                             'Xday': 98,
                             'ConfNo1': 153,
                             'ConfNo2': 168,
                             'SerialNumber': 1001,
                             'MeterNo(high)': 112,
                             'MeterNumber(low)': 1010,
                             'MeterType': 1005,
                             'MBusBotDispPriAddr': 184,
                             'MBusBotDispSecAddr': 185,
                             'CheckSum': 154,
                             'Infohour': 175,
                             }

    def read_value(self, string):
        """ Read the value from the device """
        if string in self.register_ids:
            result = self.comm.read_register(self.register_ids[string], 0)
        else:
            result = None
        return result
    def read_temp(self,):
        for i in range(10):
            try:
                result = self.comm.read_register(86, i)
                print(result)
            except:
                print('No result')
        return result

if __name__ == '__main__':
    #port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTYIWHC9-if00-port0'
    port = '/dev/serial/by-id/usb-Silicon_Labs_Kamstrup_M-Bus_Master_MultiPort_250D_131751521-if00-port0'
    multical = Multical302(port)
    #multical.read_value('Temp1')
    multical.read_temp()
