

"""
Use this command to load device
sudo modprobe usbserial vendor=0x0683 product=0x1110

Insert as automatic mount rule, as outlined in this thread
https://askubuntu.com/questions/525016/cant-open-port-dev-ttyusb0
"""

from __future__ import print_function

import sys
from time import sleep
import serial
import logging

from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)


class DataQBinary(object):

    end_char = '\r'
    read_wait_time = 0.001
    infos = {
        'vendor': 0,
        'device name': 1,
        'firmware revision': 2,
        'serial number': 6,
        'sample rate divisor': 9,
    }
    led_colors = {
        'black': 0, 'blue': 1, 'green': 2, 'cyan': 3,
        'red': 4, 'magenta': 5, 'yellow': 6, 'white': 7,
    }

    def __init__(self, device, serial_kwargs=None):
        if serial_kwargs is None:
            serial_kwargs = {}
        self.serial = serial.Serial(device, **serial_kwargs)

        # Stop any active acquisition and clear buffer
        self.stop()
        self.clear_buffer()

        # Initialize variables
        self.expect_echo = True
        self._scan_list = [0]
        self._sample_rate_divisor = int(self.info('sample rate divisor'))

    def clear_buffer(self):
        """Clear the buffer"""
        sleep(0.5)
        while self.serial.inWaiting() > 0:
            self.serial.read(self.serial.inWaiting())

    def _comm(self, arg, dont_read_reply=False):
        """Execute command and return reply"""
        # Form command and send
        command = (arg + self.end_char)
        self.serial.write(command.encode())
        LOGGER.debug("cmd: %s", command)
        if dont_read_reply:
            return ''

        # Read until reply end string
        return_string = ''
        while return_string == '' or not return_string.endswith(self.end_char):
            sleep(self.read_wait_time)
            bytes_waiting = self.serial.inWaiting()
            bytes_read = self.serial.read(bytes_waiting)
            return_string += bytes_read.decode().rstrip('\x00')
        LOGGER.debug("reply: %s", return_string)
    
        # Strip echo if present
        if self.expect_echo and return_string.startswith(arg):
            return_string = return_string.replace(arg + ' ', '', 1)

        # And finally end_char when we return the result
        return return_string.strip(self.end_char)
        

    def info(self, info_name='all'):
        """Return information about the device

        Args:
            info_name (str): Name of the requested information
                item(s). If info_name is one the specific info names,
                (the keys in DataQBinary.infos), a string will be
                returned with the value. If info_name is 'all', all
                values will be returned in a dict
        Returns:
            str or dict: Information items
        """
        if info_name == 'all':
            out = {}
            for name, number in self.infos.items():
                command = 'info {}'.format(number)
                out[name] = self._comm(command)
            return out

        if info_name not in self.infos:
            msg = 'Invalid info_name. Valid value are: {} and "all"'
            raise ValueError(msg.format(self.infos.keys()))
        command = 'info {}'.format(self.infos[info_name])
        return self._comm(command)

    def start(self):
        """Start data acquisition"""
        self.expect_echo = False
        self._comm('start 0', dont_read_reply=True)

    def stop(self):
        """Stop data acquisition

        This also implies clearing the buffer of any remaining data
        """
        self.expect_echo = True
        self._comm('stop', dont_read_reply=True)
        self.clear_buffer()

    def scan_list(self, scan_list):
        """Set the scan list

        The scan list is the list of inputs to acquire from on the
        data card. The scan list can hold up to 11 items, since there
        are a total on 11 inputs and each element can only be there
        once. The analogue input channel are numbered 0-7, 8 is the
        counter channel, 9 is the rate channel and 10 is the general
        purpose input channel. 0.7 are specified only by their number,
        8, 9 and 10 are configured specially, which is not described
        here yet.

        Args:
            scan_list (list): Etc. [3, 5, 0] for analogue input chanel 3, 5
                and 0. NOTE: The numbers are integers, not strings.
        """
        LOGGER.debug("Set scan list: %s", scan_list)
        # Check for valid scan list configuratio
        for scan_list_configuration in scan_list:
            if scan_list_configuration not in range(8):
                msg = 'Only scan list arguments 0-7 are supported'
                raise ValueError(msg)
        # Check for duplicate entries
        if len(set(scan_list)) != len(scan_list):
            msg = 'The scan list is not allowed to have duplicate entries'
            raise ValueError(msg)

        # Send the configuration
        for slot_number, configuration in enumerate(scan_list):
            command = 'slist {} {}'.format(slot_number, configuration)
            self._comm(command)

        self._scan_list = scan_list

    def sample_rate(self, rate):
        """Set the sample rate

        The value values are calculated as being in the range of

          sample rate divisor / 375   to   sample rate divisor / 65535

        So e.g. for the DI-1110 product, with a sample rate divisor of
        60,000,000, the valid inputs are in range from 915.5413 to 160000. 

        Args:
            rate (float): The sample rate given in number of elements in the scan
                list sampled per second (i.e. in Hz). Valid values depend on the
                model and is given by the "sample rate divisor" information item
                (see the info method). See information about how to calculate the
                valid input range above.

        """
        
        rate_for_command = int(self._sample_rate_divisor / float(rate))
        # Coerce in valid range
        rate_for_command = min(max(375, rate_for_command), 65535)
        self._comm('srate {}'.format(rate_for_command))

    def led_color(self, color):
        color_number = self.led_colors[color]
        command = 'led {}'.format(color_number)
        self._comm(command)

    def read(self):
        while True:
            waiting = self.serial.inWaiting()
            if waiting == 0:
                break
            bytes_read = self.serial.read(waiting)
            self._parse_data_packet(bytes_read)

    def _parse_data_packet(self, data):
        """Parse a data packet"""
        bytes_iter = iter(data)
        for n in range(8):
            byte_one = next(bytes_iter)
            byte_two = next(bytes_iter)
            if sys.version_info.major < 3:
                byte_one = ord(byte_one)
                byte_two = ord(byte_two)
            
            print(bin(byte_one))
            print(bin(byte_two))


def module_test():
    """Run primitive module tests"""
    logging.basicConfig(level=logging.DEBUG)
    global LOGGER
    LOGGER = logging.getLogger('ll')
    dataq = DataQBinary('/dev/ttyUSB0')
    print(repr(dataq.info()))
    dataq.scan_list([0, 1])
    dataq.sample_rate(1000)
    dataq.led_color('cyan')
    dataq.start()
    sleep(1)
    try:
        while True:
            dataq.read()
            break
    except KeyboardInterrupt:
        dataq.stop()
    else:
        dataq.stop()
    dataq.clear_buffer()
    


if __name__ == '__main__':
    module_test()
