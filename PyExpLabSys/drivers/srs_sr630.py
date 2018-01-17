""" Driver for Standford Research Systems, Model SR630 """
from __future__ import print_function
import serial
import time
import logging
from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

# Legal values for units
UNITS = ['ABS', 'CENT', 'FHRN', 'MDC', 'DC']

class SRS_SR630():
    """ Driver for Standford Research Systems, Model SR630 """

    def __init__(self, port):
        self.ser = serial.Serial(port, 9600, timeout=2)
        #print self.f
        #self.f.xonxoff = True
        #self.f.rtscts = False
        #self.f.dsrdtr = False
        #print self.f
        time.sleep(0.1)

    def comm(self, command):
        """ Ensures correct protocol for instrument """
        endstring = '\r'
        self.ser.write((command + endstring).encode('ascii'))
        if command.find('?') > -1:
            return_string = self.ser.readline()[:-2].decode()
        else:
            return_string = True
        return return_string

    def config_analog_channel(self, channel, follow_temperature=False, value=0):
        """ Configure an analog out channel """
        if (value < -10) or (value > 10):
            return False

        if follow_temperature:
            command = 'VMOD ' + str(channel) + ',0'
            self.comm(command)
        else:
            command = 'VMOD ' + str(channel) + ',1'
            self.comm(command)
            command = 'VOUT ' + str(channel) + ',' + str(value)
            self.comm(command)
        return True

    def set_unit(self, channel, unit):
        """ Set the measurement unit for a channel """
        if not unit in UNITS:
            return False
        command = 'UNIT ' + str(channel) + ',' + unit
        self.comm(command)
        time.sleep(0.2) # Need a bit of time to return correct unit
        return True

    def tc_types(self):
        """ List all configuration of all channels """
        types = {}
        command = 'TTYP? '
        for i in range(1, 17):
            types[i] = self.comm(command + str(i))
        return types

    def read_open_status(self):
        """ Check for open output on all channels """
        for i in range(1, 17):
            self.read_channel(i)
        command = 'OPEN?'
        # TODO: Parse the output
        open_status = bin(int(self.comm(command)))
        return open_status

    def read_serial_number(self):
        """ Return the serial number of the device """
        return self.comm('*IDN?')
    
    def read_channel(self, channel):
        """ Read the actual value of a channel """
        command = 'CHAN?'
        current_channel = self.comm(command)
        if int(current_channel) == channel:
            command = 'MEAS? ' + str(channel)
            value = self.comm(command)
        else:
            command = 'CHAN ' + str(channel)
            self.comm(command)
            command = 'MEAS? ' + str(channel)
            value = self.comm(command)
        return float(value)

if __name__ == '__main__':
    SRS = SRS_SR630('/dev/ttyUSB0')
    print(SRS.read_serial_number())
    print(str(SRS.read_channel(2)))
    print(SRS.set_unit(2, 'CENT'))
    print(str(SRS.read_channel(2)))
    print(SRS.read_open_status())
    print(SRS.tc_types())
    #print(SRS.config_analog_channel(1, follow_temperature=False, value=0.2))
