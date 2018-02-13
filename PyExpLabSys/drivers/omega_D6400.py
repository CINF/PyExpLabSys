""" Driver for Omega D6400 daq card """
from __future__ import print_function
import time
import logging
import minimalmodbus
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
LOGGER.addHandler(logging.NullHandler())

class OmegaD6400(object):
    """ Driver for Omega D6400 daq card """
    def __init__(self, address=1, port='/dev/ttyUSB0'):
        self.instrument = minimalmodbus.Instrument(port, address)
        self.instrument.serial.baudrate = 9600
        self.instrument.serial.timeout = 1.0  # Default setting leads to comm-errors
        print(self.instrument.serial)
        self.ranges = [0] * 8
        for i in range(1, 8):
            self.ranges[i] = {}
            self.ranges[i]['action'] = 'disable'
            self.ranges[i]['fullrange'] = '0'
        self.ranges[1]['action'] = 'voltage'
        self.ranges[1]['fullrange'] = '10'

        for i in range(1, 8):
            print(i)
            self.update_range_and_function(i, fullrange=self.ranges[i]['fullrange'],
                                           action=self.ranges[i]['action'])
            print('!')

    def comm(self, command, value=None):
        """ Communicates with the device """
        reply = None
        error = True

        while error is True:
            try:
                if value is None:
                    reply = self.instrument.read_register(command)
                else:
                    self.instrument.write_register(command, value)
                error = False
            except ValueError:
                LOGGER.warning('D6400 driver: Value Error')
                self.instrument.serial.read(self.instrument.serial.inWaiting())
                time.sleep(0.1)
                error = True
            except IOError:
                LOGGER.warning('D6400 driver: IOError')
                self.instrument.serial.read(self.instrument.serial.inWaiting())
                error = True
                time.sleep(0.1)
        return reply

    def read_value(self, channel):
        """ Read a measurement value from a channel """
        value = None
        reply = self.comm(47 + channel)
        if self.ranges[channel]['action'] == 'voltage':
            num_value = reply - 2 ** 15
            scale = 1.0 * 2 ** 15 / float(self.ranges[channel]['fullrange'])
            value = num_value / scale
        if self.ranges[channel]['action'] == 'tc':
            scale = 1.0 * 2 ** 16 / 1400
            value = (reply/scale) - 150
        return value

    def read_address(self):
        """ Read the RS485 address of the device """
        old_address = self.comm(0)
        return old_address


    def write_enable(self):
        """ Enable changes to setup values """
        self.comm(240, 2)
        time.sleep(0.8)
        return True

    def range_codes(self, fullrange=0, action=None):
        """ Returns the code corresponding to a given range
        """
        codes = {}
        codes['tc'] = {}
        codes['tc']['J'] = 21
        codes['tc']['K'] = 34
        codes['tc']['T'] = 23
        codes['tc']['E'] = 24
        codes['tc']['R'] = 25
        codes['tc']['S'] = 26
        codes['tc']['B'] = 27
        codes['tc']['C'] = 28
        codes['voltage'] = {}
        codes['voltage']['10'] = 1
        codes['voltage']['5'] = 2
        codes['voltage']['1'] = 3
        codes['voltage']['0.1'] = 4
        codes['voltage']['0.05'] = 5
        codes['voltage']['0.025'] = 6
        codes['disable'] = 0
        codes['current'] = 3

        if action in ('tc', 'voltage'):
            code = codes[action][fullrange]
        if action in ('disable', 'current'):
            code = codes[action]
        return code

    def update_range_and_function(self, channel, fullrange=None, action=None):
        """ Set the range and measurement type for a channel """
        if not action is None:
            self.write_enable()
            code = self.range_codes(fullrange, action)
            self.comm(95 + channel, code)
            print('##')
            time.sleep(0.1)
            self.ranges[channel]['action'] = action
            self.ranges[channel]['fullrange'] = fullrange
        return self.comm(95 + channel)

if __name__ == '__main__':
    OMEGA = OmegaD6400(1, port='/dev/ttyUSB0')
    OMEGA.update_range_and_function(1, action='voltage', fullrange='10')
    OMEGA.update_range_and_function(2, action='voltage', fullrange='10')
    print('***')
    print(OMEGA.read_value(1))
    print(OMEGA.read_value(2))
