""" Driver for Stahl HV 400 Ion Optics Supply """
from __future__ import print_function
import serial
from types import IntType # Used for type checking

class StahlHV400(object):
    """ Driver for Stahl HV 400 Ion Optics Supply """
    def __init__(self, port='/dev/ttyUSB0'):
        """ Driver for Stahl HV 400 Ion Optics Supply """
        self.serial = serial.Serial(port, 9600, timeout=0.5)
        self.serial_number = None
        self.max_voltage = None
        self.number_of_channels = None
        self.bipolar = None
        self.identify_device() # Update device info

    def comm(self, command):
        """ Perform actual communication with instrument """
        self.serial.write(command + '\r')
        reply = self.serial.readline()
        return reply[:-1]

    def identify_device(self):
        """ Return the serial number of the device """
        reply = self.comm('IDN').split(' ')
        self.serial_number = reply[0]
        self.max_voltage = int(reply[1])
        self.number_of_channels = int(reply[2])
        self.bipolar = (reply[3][0] == 'b')
        print(self.bipolar)
        return reply

    def query_voltage(self, channel):
        """ Something is all wrong here... """
        reply = self.comm(self.serial_number + ' Q' + str(channel).zfill(2))
        print(self.serial_number + ' Q' + str(channel).zfill(2))
        return reply

    def set_voltage(self, channel, value):
        """ Set the voltage of a channel """
        if self.bipolar:
            fraction = float(value) / (2 * self.max_voltage) + 0.5
        else:
            fraction = float(value) / self.max_voltage
        assert type(channel) is IntType
        print(self.comm(self.serial_number + ' CH' + str(channel).zfill(2) +
                        ' ' + '{0:.6f}'.format(fraction)))

    def read_temperature(self):
        """ Read temperature of device """
        reply = self.comm(self.serial_number + ' TEMP')
        temperature = reply[4:-2] # Remove word TEMP and unit
        return float(temperature)

    def check_channel_status(self):
        """ Check status of channel """
        self.comm(self.serial_number + 'LOCK')

if __name__ == '__main__':
    HV400 = StahlHV400('/dev/ttyUSB0')
    HV400.set_voltage(1, 0)
    print(HV400.read_temperature())
    print('----')
    print(HV400.query_voltage(1))
