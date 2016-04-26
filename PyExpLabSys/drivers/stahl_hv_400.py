""" Driver for Stahl HV 400 Ion Optics Supply """
from __future__ import print_function
import serial
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

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
        error = 20
        while error > 0:
            try:
                reply = self.comm(self.serial_number + ' Q' + str(channel).zfill(2))
                value = float(reply[:-1].replace(',', '.'))
                error = -1
            except ValueError:
                error = error - 1
                value = '-99999'
        return value

    def set_voltage(self, channel, value):
        """ Set the voltage of a channel """
        if self.bipolar:
            fraction = float(value) / (2 * self.max_voltage) + 0.5
        else:
            fraction = float(value) / self.max_voltage
        assert isinstance(channel, int)
        self.comm(self.serial_number + ' CH' + str(channel).zfill(2) +
                  ' ' + '{0:.6f}'.format(fraction))
        command = self.serial_number + ' DIS L CH' + str(channel).zfill(2) + ' {0:.2f}V'
        self.comm(command.format(value))
        return True # Consider to run check_channel_status

    def read_temperature(self):
        """ Read temperature of device """
        reply = self.comm(self.serial_number + ' TEMP')
        temperature = reply[4:-2] # Remove word TEMP and unit
        return float(temperature)

    def check_channel_status(self):
        """ Check status of channel """
        reply = self.comm(self.serial_number + ' LOCK')
        channel_1_4 = bin(ord(reply[0]))[-4:]
        channel_5_8 = bin(ord(reply[1]))[-4:]
        channel_status = {}
        channel_status[4] = channel_1_4[0] == '0'
        channel_status[3] = channel_1_4[1] == '0'
        channel_status[2] = channel_1_4[2] == '0'
        channel_status[1] = channel_1_4[3] == '0'
        channel_status[8] = channel_5_8[0] == '0'
        channel_status[7] = channel_5_8[1] == '0'
        channel_status[6] = channel_5_8[2] == '0'
        channel_status[5] = channel_5_8[3] == '0'
        return channel_status

if __name__ == '__main__':
    HV400 = StahlHV400('/dev/ttyUSB0')
    HV400.set_voltage(1, -159.1)
    HV400.set_voltage(2, -69.1)
    #HV400.set_voltage(3, -47.9) # 55.9
    #HV400.set_voltage(4, -47.9) # 46.9
    #HV400.set_voltage(5, -44.9) # 44.9
    #HV400.set_voltage(6, 0)
    #HV400.set_voltage(7, 0)
    #HV400.set_voltage(8, 0)
    #print(HV400.read_temperature())
    print(HV400.check_channel_status())
    status = (HV400.check_channel_status())
    print(False in status)
    #print(HV400.query_voltage(1))
    #print(HV400.query_voltage(2))
    #print(HV400.query_voltage(3))
    #print(HV400.query_voltage(4))
    #print(HV400.query_voltage(5))
    #print(HV400.query_voltage(6))
    #print(HV400.query_voltage(7))
    #print(HV400.query_voltage(8))
