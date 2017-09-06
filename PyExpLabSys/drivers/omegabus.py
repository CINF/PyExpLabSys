""" Driver for OmegaBus devices """
from __future__ import print_function
import time
import logging
import serial
from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

class OmegaBus(object):
    """ Driver for OmegaBus devices """
    def __init__(self, device='/dev/ttyUSB0', model='D5251', baud=300):
        self.ser = serial.Serial(device, baud)
        self.setup = {}
        self.setup['model'] = model
        self.read_setup() # Read temperature unit, if relevant
        time.sleep(0.1)

    def comm(self, command):
        """ Handles serial protocol """
        command = command + "\r"
        command = command.encode('ascii')
        self.ser.write(command)
        time.sleep(1)
        answer = self.ser.read(self.ser.inWaiting())
        answer = answer.decode()
        return answer

    def read_value(self, channel, convert_to_celcius=True):
        """ Read the measurement value """
        value_string = self.comm("$" + str(channel) + "RD")
        # The value string is after the *
        if '*' in value_string:
            value_string = value_string.split('*', 1)[1]
        value = float(value_string)
        if convert_to_celcius and self.setup['model'] in ['D5311', 'D5321', 'D5331', 'D5431']:
            if self.setup['temp_unit'] == 'F':
                value = 5 * (value - 32)/9
        return value

    def read_max(self, channel):
        """ The maximum read-out value """
        temp_string = self.comm("$" + str(channel) + "RMX")
        if temp_string[1] == "*":
            temp_string = temp_string[3:]
        return float(temp_string)

    def read_min(self, channel):
        """ The minimum read-out value """
        temp_string = self.comm("$" + str(channel) + "RMN")
        if temp_string[1] == "*":
            temp_string = temp_string[2:]
        return float(temp_string)

    def read_setup(self):
        """ Read Device setup information """
        rs_string = self.comm("$" + "1RS")

        if '*' in rs_string:
            rs_string = rs_string.split('*', 1)[1]

        byte1 = rs_string[0:2]
        byte2 = rs_string[2:4]
        byte3 = rs_string[4:6]
        #byte4 = rs_string[6:8]

        setupstring = ""
        setupstring += "Base adress: " + chr(int(byte1, 16)) + "\n"

        bits_2 = (bin(int(byte2, 16))[2:]).zfill(8)
        setupstring += "No linefeed\n" if bits_2[0] == '0' else "Linefeed\n"
        if bits_2[2] == '0': #bits_2[1] will contain the parity if not none
            setupstring += "Parity: None"  + "\n"
        setupstring += "Normal addressing\n" if bits_2[3] == '0' else "Extended addressing\n"
        if bits_2[4:8] == '0010':
            setupstring += "Baud rate: 9600"  + "\n"

        bits_3 = (bin(int(byte3, 16))[2:]).zfill(8)

        setupstring += "Channel 3 enabled\n" if bits_3[0] == '1' else "Channel 3 disabled\n"
        setupstring += "Channel 2 enabled\n" if bits_3[1] == '1' else "Channel 2 disabled\n"
        setupstring += "Channel 1 enabled\n" if bits_3[2] == '1' else "Channel 1 disabled\n"
        if bits_3[3] == '1':
            setupstring += "No cold junction compensation\n"
        else:
            setupstring += "Cold junction compensation enabled\n"
        setupstring += "Unit: Fahrenheit\n" if bits_3[4] == '1' else "Unit: Celsius\n"
        if bits_3[4] == '1':
            self.setup['temp_unit'] = 'F'
        else:
            self.setup['temp_unit'] = 'C'
        #print (bin(int(byte4,16))[2:]).zfill(8
        return setupstring


if __name__ == "__main__":
    OMEGA = OmegaBus(model='D5251')
    print(OMEGA.read_setup())
    print(OMEGA.read_value(1))
    print(OMEGA.read_value(2))
    print(OMEGA.read_value(3))
    print(OMEGA.read_value(4))
    #print(OMEGA.read_min(1))
    #print(OMEGA.read_max(1))
