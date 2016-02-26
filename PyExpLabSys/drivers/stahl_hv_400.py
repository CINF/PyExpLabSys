""" Driver for Stahl HV 400 Ion Optics Supply """
from __future__ import print_function
import serial

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
        command = command + '\r'
        command = command.encode('ascii')
        reply = ''
        iterations = 0
        while (len(reply) < 2) and (iterations < 20):
            self.serial.write(command)
            reply = self.serial.readline()
            reply = reply.decode('latin-1')
            iterations = iterations + 1 # Make sure not to end in infinite lop
        return reply[:-1]

    def identify_device(self):
        """ Return the serial number of the device """
        reply = self.comm('IDN')
        reply = reply.split()
        self.serial_number = reply[0]
        self.max_voltage = int(reply[1])
        self.number_of_channels = int(reply[2])
        self.bipolar = (reply[3][0] == 'b')
        return reply

    def query_voltage(self, channel):
        """ Something is all wrong here... """
        reply = self.comm(self.serial_number + ' Q' + str(channel).zfill(2))
        #print(self.serial_number + ' Q' + str(channel).zfill(2))
        return reply

    def set_voltage(self, channel, value):
        """ Set the voltage of a channel """
        if self.bipolar:
            fraction = float(value) / (2 * self.max_voltage) + 0.5
        else:
            fraction = float(value) / self.max_voltage
        assert isinstance(channel, int)
        self.comm(self.serial_number + ' CH' + str(channel).zfill(2) +
                  ' ' + '{0:.6f}'.format(fraction))
        return True # Consider to run check_channel_status

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
    print(HV400.query_voltage(1))
