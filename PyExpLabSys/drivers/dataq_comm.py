# pylint: disable=R0204
""" Driver for DATAQ dac units """
from __future__ import print_function
import time
import logging
import serial
from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

class DataQ(object):
    """ driver for the DataQ Instrument """
    def __init__(self, port):
        self.serial = serial.Serial(port)
        self.set_float_mode() # This is currently the only implemented mode
        self.scan_list_counter = 0
        self.stop_measurement()
        self.scanning = False
        self.reset_scan_list()
        self.scan_list = []
        time.sleep(1)
        self.serial.read(self.serial.inWaiting()) # Clear the read-buffer

    def comm(self, command):
        """ comm function """
        end_char = '\r' # carriage return
        command = command  + end_char
        command = command.encode()
        self.serial.write(command)
        return_string = b''
        current_char = chr(0)
        while ord(current_char) != ord(end_char):
            current_char = self.serial.read(1)
            return_string += current_char
        return return_string.decode('ascii')

    def dataq(self):
        """ Returns the string DATAQ"""
        command = 'info 0'
        res = self.comm(command)[7:]
        return res

    def device_name(self):
        """ Returns device name"""
        command = 'info 1'
        res = self.comm(command)[7:]
        return res

    def firmware(self):
        """ Returns firmware version """
        command = 'info 2'
        res = self.comm(command)[7:]
        return res

    def serial_number(self):
        """ Returns device serial number """
        command = 'info 6'
        res = self.comm(command)[7:]
        return res

    def start_measurement(self):
        """ Start a measurement scan """
        command = 'start'
        res = self.comm(command)
        self.scanning = True
        return res

    def read_measurements(self):
        """ Read the newest measurents """
        if not self.scanning:
            return False
        #data = self.serial.read(self.serial.inWaiting())
        data_start = '   '
        while data_start != b'sc ':
            data_start = self.serial.read(3)
        scan_data = b' '
        try: # Python 2
            ord(scan_data[-1])
            end_char = '\r'
        except TypeError: #Python 3
            end_char = 13
        while scan_data[-1] != end_char:
            scan_data += self.serial.read(1)
        scan_data = scan_data.decode('ascii')
        # Remove double spaces to have a unique split identifier
        scan_data = scan_data.strip().replace('  ', ' ')
        scan_data = scan_data.split(' ')
        scan_values = [float(i) for i in scan_data]
        return_values = {}
        for i in range(0, len(scan_values)):
            return_values[self.scan_list[i]] = scan_values[i]
        return return_values

    def stop_measurement(self):
        """ Stop a measurement scan """
        command = 'stop'
        res = self.comm(command)
        self.scanning = False
        return res

    def add_channel(self, channel):
        """ Adds a channel to scan slist.
        So far only analog channels are accepted """
        command = 'slist ' + str(self.scan_list_counter) + ' x000' + str(channel - 1)
        # TODO: This is a VERY rudementary treatment of the scan-list...
        self.scan_list_counter = self.scan_list_counter + 1
        self.scan_list.append(channel)
        res = self.comm(command)
        return res

    def set_ascii_mode(self):
        """ change response mode to ACSII"""
        command = 'asc'
        res = self.comm(command)
        return res

    def set_float_mode(self):
        """ change response mode to float"""
        command = 'float'
        res = self.comm(command)
        return res

    def reset_scan_list(self):
        """ Reseting the scan list """
        command = 'slist 0 0xffff'
        self.scan_list_counter = 0
        self.scan_list = []
        res = self.comm(command)
        return res

    """
    def set_multiple_output(self, value):
        command = 'dout ' + value
        res = self.comm(command)
        return res

    def set_single_output(self, ch):
        if ch == '0':
            value = '14'
        elif ch == '1':
            value = '13'
        elif ch == '2':
            value = '11'
        elif ch == '3':
            value = '08'
        command = 'dout ' + value
        res = self.comm(command)
        return res
    
    def set_outputs(self, ch0=False, ch1=False, ch2=False, ch3=False):
        value = 15 - int(ch0)*2**0 - int(ch1)*2**1 - int(ch2)*2**2 - int(ch3)*2**3
        command = 'dout ' + str(value)
        res = self.comm(command)
        return res
     """

if __name__ == '__main__':
    DATAQ = DataQ('/dev/ttyACM0')
    print(DATAQ.device_name())
    print(DATAQ.firmware())
    print(DATAQ.serial_number())
    DATAQ.add_channel(1)
    DATAQ.add_channel(2)
    DATAQ.add_channel(3)
    DATAQ.add_channel(4)
    print(DATAQ.start_measurement())
    for _ in range(0, 100000):
        print(DATAQ.read_measurements())
    DATAQ.stop_measurement()
