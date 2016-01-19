import serial
import time
from types import *

class Stahl_HV_400():

    def __init__(self, port='/dev/ttyUSB0'):
        self.f = serial.Serial(port, 9600, timeout=0.5)
        self.sn = None
        self.max_voltage = None
        self.number_of_channels = None
        self.bipolar = None
        self.identify_device() # Update device info
        
    def comm(self, command):
        self.f.write(command + '\r')
        reply = self.f.readline()
        return reply[:-1]

    def identify_device(self):
        """ Return the serial number of the device """
        reply = self.comm('IDN').split(' ')
        self.sn = reply[0]
        self.max_voltage = int(reply[1])
        self.number_of_channels = int(reply[2])
        self.bipolar = (reply[3][0] == 'b')
        print(self.bipolar)
        return reply
 
    def query_voltage(self, channel):
        """ Something is all wrong here... """
        reply = self.comm(self.sn + ' Q' + str(channel).zfill(2))
        print(self.sn + ' Q' + str(channel).zfill(2))
        return reply
 
    def set_voltage(self, channel, value):
        """ Set the voltage of a channel """
        if self.bipolar:
            fraction = float(value) / (2 * self.max_voltage) + 0.5
        else:
            fraction = float(value) / self.max_voltage

        assert type(channel) is IntType
        print(self.comm(self.sn + ' CH' + str(channel).zfill(2) +
              ' ' + '{0:.6f}'.format(fraction)))
              
    def read_temperature(self):
        reply = self.comm(self.sn + ' TEMP')
        temperature = reply[4:-2] # Remove word TEMP and unit
        return float(temperature)

    def check_channel_status(self):
        self.comm(self.sn + 'LOCK')

if __name__ == '__main__':
    HV400 = Stahl_HV_400('/dev/ttyUSB0')
    HV400.set_voltage(1, -75)
    HV400.set_voltage(2, -50)
    HV400.set_voltage(3, -25)
    HV400.set_voltage(4, 0)
    HV400.set_voltage(5, 25)
    HV400.set_voltage(6, 50)
    HV400.set_voltage(7, 75)
    HV400.set_voltage(8, 100)
    print(HV400.read_temperature())
    print('----')
    print(HV400.query_voltage(1))
    print(HV400.query_voltage(2))
    print(HV400.query_voltage(3))
    print(HV400.query_voltage(4))
    print(HV400.query_voltage(5))
    print(HV400.query_voltage(6))
    print(HV400.query_voltage(7))
    print(HV400.query_voltage(8))

    
        
