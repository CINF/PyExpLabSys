# -*- coding: utf-8 -*-
""" This module contains drivers for equipment from Omega. Specifically it
contains a driver for the ??? thermol couple read out unit.
"""


import time
import logging
import serial


LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
#LOGGER.addHandler(logging.NullHandler())
LOGGER.addHandler(logging.StreamHandler())


class ISeries(object):
    """Driver for the iSeries omega temperature controllers"""

    pre_string = chr(42)
    end_string = chr(13)

    def __init__(self, port, baudrate=19200, comm_stnd='rs485'):
        """Initialize internal parameters

        :param port: A serial port designation as understood by `pySerial
            <http://pyserial.sourceforge.net/pyserial_api.html#native-ports>`_
        """
        LOGGER.debug('Initialize driver')
        self.serial = serial.Serial(port, baudrate, bytesize=serial.SEVENBITS,
                                    parity=serial.PARITY_ODD,
                                    stopbits=serial.STOPBITS_ONE,
                                    timeout=2)
        self.comm_stnd = comm_stnd
        time.sleep(0.1)
        LOGGER.info('Driver initialized')

    def command(self, command, response_length=None):
        """Run a command and return the result

        :param command: The command to execute
        :type command: str
        :param response_length: The expected legth of the response. Will force
            the driver to wait untill this many characters is ready as a
            response from the device.
        :type response_length: int
        """

        # Hints for rs485 implementation in the bottom of this file

        LOGGER.debug('command called with {}, {}'.format(command,
                                                         response_length))
        self.serial.write(self.pre_string + command + self.end_string)
        if response_length is not None:
            while self.serial.inWaiting() < response_length + 1:
                # If faster replies are needed this can be lowered to e.g. 0.05
                time.sleep(0.17)
        else:
            # If a response length is not given, assume that the command can be
            # executed in 0.5 seconds
            time.sleep(0.5)
        response = self.serial.read(self.serial.inWaiting())
        # Strip \r from responseRemove the echo response from the device
        LOGGER.debug('comand return {}'.format(response[:-1]))
        if response[0:len(command)] == command:
            response = response[len(command):]
        return response[:-1]

    def reset_device(self):
        """Reset the device"""
        command = 'Z02'
        return self.command(command)

    def identify_device(self):
        """Return the identity of the device"""
        command = 'R26'
        return self.command(command)

    def read_temperature(self):
        """Return the temperature"""
        LOGGER.debug('read_temperature called')
        command = 'X01'
        try:
            response = float(self.command(command, response_length=5))
        except ValueError:
            print 'AAA'
            response = None
        LOGGER.debug('read_temperature return {}'.format(response))
        return response


    def close(self):
        """Close the connection to the device"""
        LOGGER.debug('Driver asked to close')
        self.serial.close()
        LOGGER.info('Driver closed')



class CNi3244_C24(ISeries):
    """Driver for the CNi3244_C24 device"""

    def __init__(self, port):
        """Initialize internal parameters

        :param port: A serial port designation as understood by `pySerial
            <http://pyserial.sourceforge.net/pyserial_api.html#native-ports>`_
        """        
        super(CNi3244_C24, self).__init__(port)

"""
def comm(self,command, address=1):
pre_string = chr(42)
end_string = chr(13)
if self.comm_stnd == 'rs485':
length_command = len(command) + 2
else:
length_command = len(command)
if self.comm_stnd == 'rs485':
comm_string = pre_string + '0' + str(address) + command + end_string
else:
comm_string = pre_string + command + end_string
self.f.write(comm_string)
"""
