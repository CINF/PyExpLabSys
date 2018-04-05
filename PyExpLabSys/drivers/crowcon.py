"""This module contains a driver for the Vortex gas alarm central

Copyright 2014 CINF (https://github.com/CINF)

This Vortex driver is part of PyExpLabSys.

PyExpLabSys is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyExpLabSys is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PyExpLabSys.  If not, see <http://www.gnu.org/licenses/>.


The documentation for the Vortex is the property of and copyrighted to Crowcon:
http://www.crowcon.com/

.. seealso:: Docs for this implementation are on the wiki at:
    https://cinfwiki.fysik.dtu.dk/cinfwiki/Equipment#Vortex_Gas_Alarm_System
    or online at:
    http://www.crowcon.com/uk/products/control-panels/vortex.html

"""

from __future__ import print_function, unicode_literals

import logging
from collections import namedtuple
from minimalmodbus import Instrument, _numToTwoByteString, _twoByteStringToNum
from PyExpLabSys.common.supported_versions import python2_and_3

# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)


# These named tuples are used for multiple return values
Status = namedtuple('Status', ['code', 'value'])  # pylint: disable=C0103
DetConfMap = namedtuple(  # pylint: disable=C0103
    'DetectorConfigurationMap',
    ['number', 'identity', 'enabled', 'type', 'unit', 'range', 'level1', 'transition1',
     'level2', 'transition2', 'level3', 'transition3',]
)
# pylint: disable=C0103
DetLev = namedtuple('DetectorLevels', ['number', 'level', 'status', 'inhibit'])


### Utility functions
def register_to_bool(register):
    """Convert a register value to a boolean

    0 is considered False, 65535 True and remaining integer values are invalid.

    Args:
        register (int): The register value

    Returns:
        bool: The boolean value
    """
    if register == 0:  # Hex value 0000
        return False
    elif register == 65535:  # Hex value FFFF
        return True
    else:
        raise ValueError('Only 0 or 65535 can be converted to a boolean')


# pylint: disable=R0904
class Vortex(Instrument):
    """Driver for the Vortex gas alarm central

    .. note:: In the manual the register numbers are 1-based, but when sent to minimal
        modbus they need to be 0 based.
    """

    def __init__(self, serial_device, slave_address, debug=False, cache=True, retries=3):
        """Initialize the driver

        Args:
            serial_device (str): The serial device to use
            slave_address (int): The address of the slave device
            debug (bool): Whether debugging output from minimal modbus should be enabled
            cache (bool): Whether system configuration values (which are expected not to
                change within the runtime of the program) should be cached

        """
        LOGGER.info('__init__ called, serial device: %s, slave address: %s',
                    serial_device, slave_address)
        Instrument.__init__(self, serial_device, slave_address)
        self.serial.baudrate = 9600
        self.serial.stopbits = 2
        self.serial.timeout = 2.0
        self.retries = retries
        # Variables
        self.debug = debug
        self.cache = cache
        # Cache
        self.system_conf = {}
        self.channel_conf = {}
        LOGGER.info('__init__ complete')

    def close(self):
        """Close the serial communication connection"""
        LOGGER.info('close called')
        self.serial.close()
        LOGGER.info('close complete')

    def read_register(self, *args, **kwargs):
        """Read register from instrument (with retries)

        The argument definition is the same as for the minimalmodbus method, see the full
        documentation for `read_register
        <https://minimalmodbus.readthedocs.io/en/master/apiminimalmodbus
        .html#minimalmodbus.Instrument.read_register>`_ for details.

        """
        for retry in range(0, self.retries + 1):
            try:
                return Instrument.read_register(self, *args, **kwargs)
            except ValueError as exception:
                if retry < self.retries:
                    LOGGER.warning("Communication error in read_register, retrying %s "
                                   "out of %s times", retry + 1, self.retries)
                    continue
                else:
                    raise exception

    def read_string(self, *args, **kwargs):
        """Read string from instrument (with retries)

        The argument definition is the same as for the minimalmodbus method, see the full
        documentation `read_string
        <https://minimalmodbus.readthedocs.io/en/master/apiminimalmodbus
        .html#minimalmodbus.Instrument.read_string>`_ for details.

        """
        for retry in range(0, self.retries + 1):
            try:
                return Instrument.read_string(self, *args, **kwargs)
            except ValueError as exception:
                if retry < self.retries:
                    LOGGER.warning("Communication error in read_string, retrying %s "
                                   "out of %s times", retry + 1, self.retries)
                    continue
                else:
                    raise exception

    def read_bool(self, register):
        """Read int from register and convert to boolean value

        0 is considered False, 65535 True and remaining integer values are
        invalid.

        Args:
            register (int): The register to read from

        Returns:
            bool: The boolean value
        """
        LOGGER.debug('read_bool at register %s', register)
        boolean = register_to_bool(self.read_register(register))
        LOGGER.debug('read_bool %s', boolean)
        return boolean

    def _check_detector_number(self, detector_number):
        """Check for a valid detector number"""
        num_detectors = self.get_number_installed_detectors()
        if detector_number not in range(1, num_detectors + 1):
            raise ValueError('Only detector numbers 1-{} are valid'.format(num_detectors))

    # System commands, manual section 4.5.1
    def get_type(self):
        """Get the device type

        Returns:
            str: The type of the device e.g. 'Vortex'
        """
        LOGGER.info('get_type called')
        type_string = self.read_string(0, numberOfRegisters=8)
        LOGGER.debug('get_type read %s', type_string)
        return type_string

    def get_system_status(self):
        """Get the system status

        Returns:
            list: ['All OK'] if no status bits (section 5.1.1 in the manual) has been set,
                otherwise one string for each of the status bits that was set.
        """
        LOGGER.info('get_system_status called')
        status = self.read_register(11)
        status_list = []
        if status == 0:
            status_list.append('All OK')
        else:
            # Format the number into bitstring and reverse it with [::-1]
            bit_string = '{:016b}'.format(status)[::-1]
            for position, status_message in SYSTEM_STATUS.items():
                if bit_string[position] == '1':
                    status_list.append(status_message)
        LOGGER.debug('get_system_status read: %s', status_list)
        return status_list

    def get_system_power_status(self):
        """Get the system power status

        Returns:
            Status: A Status named tuple containing status code and string
        """
        LOGGER.info('get_system_power_status called')
        value = self.read_register(12)
        status = SYSTEM_POWER_STATUS.get(value, 'Unknown status value')
        status_tuple = Status(value, status)
        LOGGER.debug('get_system_power_status returned: %s', status_tuple)
        return status_tuple

    def get_serial_number(self):
        """Get the serial number

        Returns:
            str: The serial number
        """
        LOGGER.info('get_serial_number called')
        serial_number = self.read_string(32, numberOfRegisters=8)
        LOGGER.debug('get_serial_number returned: %s', serial_number)
        return serial_number

    def get_system_name(self):
        """Get the serial number

        Returns:
            str: The system name
        """
        LOGGER.info('get_system_name called')
        system_name = self.read_string(33, numberOfRegisters=8)
        LOGGER.debug('get_system_name returned: %s', system_name)
        return system_name

    def get_number_installed_detectors(self):
        """Get the number of installed detector inputs

        This value is cached if requested. See docstring for :meth:`__init__`.

        Returns:
            int: The number of installed detectors
        """
        LOGGER.info('get_number_installed_detectors called')
        if self.cache:
            if 'installed_detectors' not in self.system_conf:
                LOGGER.debug('num det. not in cache')
                self.system_conf['installed_detectors'] = self.read_register(38)

            LOGGER.debug('num det. return: %s', self.system_conf['installed_detectors'])
            return self.system_conf['installed_detectors']
        else:
            number = self.read_register(38)
            LOGGER.debug('num det. return un-cached: %s', number)
            return number

    # pylint: disable=C0103
    def get_number_installed_digital_outputs(self):
        """Get the number of installed digital outputs

        Returns:
            int: The number of installed digital inputs
        """
        LOGGER.info('get_number_installed_digital_outputs called')
        num_digital_outputs = self.read_register(39)
        LOGGER.debug('get_number_installed_digital_outputs returned: %s',
                     num_digital_outputs)
        return num_digital_outputs

    # Detector configuration commands, manual section e.g 4.5.2
    def detector_configuration(self, detector_number):
        """Read detector configuration

        This value is cached if requested. See docstring for :meth:`__init__`.

        Args:
            detector_number (int): The detector number. Detectors numbers are one based

        Returns:
            DetConfMap: Named tuple (DetConfMap) containing the detector configuration
        """
        LOGGER.info('detector_configuration called for detector: %s', detector_number)
        self._check_detector_number(detector_number)

        # Return cached value if cache is True and it has been cached
        if self.cache and detector_number in self.channel_conf:
            LOGGER.debug('detector_configuration returned cached value: %s',
                         self.channel_conf[detector_number])
            return self.channel_conf[detector_number]

        # The registers for the detectors are shifted by 20 for each
        # detector and the register numbers below are for detector 1
        reg_shift = 20 * (detector_number - 1)
        reg = {}
        reg['enabled']     = 109 + reg_shift  # pylint: disable=bad-whitespace
        reg['type']        = 110 + reg_shift  # pylint: disable=bad-whitespace
        reg['level1']      = 113 + reg_shift  # pylint: disable=bad-whitespace
        reg['transition1'] = 114 + reg_shift  # pylint: disable=bad-whitespace
        reg['level2']      = 115 + reg_shift  # pylint: disable=bad-whitespace
        reg['transition2'] = 116 + reg_shift  # pylint: disable=bad-whitespace
        reg['level3']      = 117 + reg_shift  # pylint: disable=bad-whitespace
        reg['transition3'] = 118 + reg_shift  # pylint: disable=bad-whitespace
        reg['unit']        = 121 + reg_shift  # pylint: disable=bad-whitespace
        reg['range']       = 122 + reg_shift  # pylint: disable=bad-whitespace
        reg['identity']    = 125 + reg_shift  # pylint: disable=bad-whitespace

        values = {'number': detector_number}
        # Read if the detector is enabled
        values['enabled'] = self.read_bool(reg['enabled'])
        # Read the detector type
        values['type'] = DETECTOR_TYPE.get(self.read_register(reg['type']),
                                           'Unknown Detector Type')
        # Read the units
        values['unit'] = UNITS.get(self.read_register(reg['unit']), 'Unknown Unit')
        # Read the range and do not allow unknown range
        range_register = self.read_register(reg['range'])
        try:
            values['range'] = RANGE[range_register]
        except KeyError:
            message = 'Unknown range code {}. Valid values are 9-25'
            raise ValueError(message.format(range_register))
        # Read the identity string
        values['identity'] = self.read_string(reg['identity'], numberOfRegisters=4)
        values['identity'] = values['identity'].rstrip('\x00')

        # Read alarm levels and transition types
        for number in range(1, 4):
            level = 'level' + str(number)
            transition = 'transition' + str(number)
            values[level] = self.read_register(reg[level], numberOfDecimals=3, signed=True)\
                            * values['range']
            values[transition] = TRANSITION[self.read_bool(reg[transition])]

        # Wrap in named tuple
        named_tuple_out = DetConfMap(**values)

        if self.cache:
            LOGGER.debug('detector_configuration save cached value: %s', named_tuple_out)
            self.channel_conf[detector_number] = named_tuple_out

        LOGGER.debug('detector_configuration return: %s', named_tuple_out)
        return named_tuple_out

    # Detector levels commands, manual section e.g: 4.5.14
    def get_detector_levels(self, detector_number):
        """Read detector levels

        Args:
            detector_number (int): The number of the detector to get the levels
                of

        Returns:
            namedtuple: DetLev named tuple containing the detector number, detector level,
                a list of status messages and a boolean that describes whether the
                detector is inhibited
        """
        LOGGER.debug('get_detector_levels called for detector: %s', detector_number)
        self._check_detector_number(detector_number)

        # The registers for the detectors are shfited by 10 for each
        # register and the register numbers below are for detector 1
        reg_shift = 10 * (detector_number - 1)

        # Get the range and read the level
        detector_range = self.detector_configuration(detector_number).range
        level = self.read_register(2999 + reg_shift, numberOfDecimals=3, signed=True)\
                * detector_range

        # Read the status register and form the list of status messages
        status = self.read_register(3000 + reg_shift)
        status_out = []
        if status == 0:
            status_out.append('OK')
        else:
            # Format the number into bitstring and reverse it with [::-1]
            bit_string = '{:016b}'.format(status)[::-1]
            for bit_position, status_message in DETECTOR_STATUS.items():
                if bit_string[bit_position] == '1':
                    status_out.append(status_message)

        # Read inhibited
        inhibited = self.read_bool(3003 + reg_shift)

        # Form detector levels named tuple
        detector_levels = DetLev(detector_number, level, status_out, inhibited)
        LOGGER.debug('get_detector_levels return: %s', detector_levels)
        return detector_levels


    def get_multiple_detector_levels(self, detector_numbers):
        """Get the levels for multiple detectors in one communication call

        Args:
            detector_numbers (sequence): Sequence of integer detector numbers (remembe
                they are 1 based)

        .. warning::
           This method uses "hidden" functions in the minimal modbus module for value
           conversion. As they are hidden, they are not guarantied to preserve their
           interface, which means that this method may break at any time

        """
        # Check for valid detector numbers
        for detector_number in detector_numbers:
            self._check_detector_number(detector_number)

        # We read 10 registers per detector
        # FIXME. This may exceed the maximum number of registers that can be read
        data = self.read_registers(2999, len(detector_numbers) * 10)

        detector_levels = {}
        for detector_number in detector_numbers:
            # Calculate the register shift for this detector. There are 10 registers
            # per detector, in order.
            reg_shift = 10 * (detector_number - 1)

            # Get the range and read the level
            detector_range = self.detector_configuration(detector_number).range
            # The level is the 0th register
            level_register = data[reg_shift]
            bytestring = _numToTwoByteString(level_register)
            level = _twoByteStringToNum(bytestring, numberOfDecimals=3, signed=True)\
                    * detector_range

            # Status is the 1st register (0-based)
            status = data[1 + reg_shift]
            status_out = []
            if status == 0:
                status_out.append('OK')
            else:
                # Format the number into bitstring and reverse it with [::-1]
                bit_string = '{:016b}'.format(status)[::-1]
                for bit_position, status_message in DETECTOR_STATUS.items():
                    if bit_string[bit_position] == '1':
                        status_out.append(status_message)

            # inhibit is the 4th register (0-based)
            inhibited_register = data[4 + reg_shift]
            inhibited = register_to_bool(inhibited_register)

            # Form the detector levels named tuple and put in output dict
            detector_level = DetLev(detector_number, level, status_out, inhibited)
            detector_levels[detector_number] = detector_level

        return detector_levels


# System power status translations, section 4.5.1
SYSTEM_POWER_STATUS = {
    0: 'OK',
    1: 'Main supply OK, battery low',
    2: 'Main supply fail, battery good',
    3: 'Main supply OK, battery disconnected',
    4: 'Main supply fail, battery low',
    5: 'No Comms to Power Card',
}

# Detector type, section e.g. 4.5.2
DETECTOR_TYPE = {
    0: 'Not Configured',
    6: 'Gas',
    8: 'Fire',
}

# Detector units, manual section e.g. 4.5.2
UNITS = {
    0: '%LEL',
    1: '%VOL',
    2: 'PPM',
    3: 'Fire',
}

# Detector range, manual section e.g. 4.5.2
RANGE = {
    9: 1.0,
    10: 2.0,
    11: 2.5,
    12: 5.0,
    13: 10.0,
    14: 20.0,
    15: 25.0,
    16: 50.0,
    17: 100.0,
    18: 200.0,
    19: 250.0,
    20: 500.0,
    21: 1000.0,
    22: 2000.0,
    23: 2500.0,
    24: 5000.0,
    25: 10000.0,
}

# Detector transition type, manual section e.g. 4.5.2
TRANSITION = {
    True: 'Rising',
    False: 'Failing',
}

# Detector status, section 5.1.7
DETECTOR_STATUS = {
    0: 'Alarm 1 present',
    1: 'Alarm 2 present',
    2: 'Alarm 3 present',
    3: 'Detector level interpreted as inhibit',
    4: 'Detector level interpreted as Low Info',
    5: 'Detector level interpreted as High Info',
    6: 'Low End Fault',
    7: 'High End Fault',
    8: 'Detector I2C fault',
    9: 'Detector Inhibit from controller (inhibit button pushed or inhibited from comms link)',
}

# System status, manual section 5.1.1
SYSTEM_STATUS = {
    0: 'Vortex system is in channel test',
    1: 'Vortex system is in jump hold',
    2: 'Vortex system has a system fault',
    3: 'System fault is a battery fault',
    4: 'System fault is a FRAM data integrity fault',
    5: 'System fault is an internal I2C bus fault',
    6: 'System fault is a display access fault',
    7: 'System fault is a power monitor access fault',
    8: 'System fault is an external I2C bus fault',
    9: 'System fault is a relay board fault',
}


def main():
    """Main function, used to simple functional test"""
    from pprint import pprint
    from time import time

    #logging.basicConfig(level=logging.DEBUG)
    #logging.debug('Start')

    vortex = Vortex('/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTY3G9FE-if00-port0', 2, cache=False)
    vortex.debug = True

    while True:
        vortex.read_bool(109)#detector_configuration(1)
        #print("####################")
        #print('Power status :', vortex.get_system_power_status())
        #vortex.get_detector_levels(1)

    #print('serial version:', serial.__version__)
    #print('serial module:', serial)

    print('Type         :', vortex.get_type())
    print('System status:', vortex.get_system_status())
    print('Power status :', vortex.get_system_power_status())
    print('Serial number:', vortex.get_serial_number())
    print('System name  :', vortex.get_system_name())
    print()
    print('Number of installed detectors      :', vortex.get_number_installed_detectors())
    print('Number of installed digital outputs:',
          vortex.get_number_installed_digital_outputs())
    print()
    for detector_number in range(1, 9):
        print('Detector', detector_number)
        print(vortex.detector_configuration(detector_number))
        print(vortex.get_detector_levels(detector_number), end='\n\n')

    print('get_multiple_detector_levels')
    t0 = time()
    while True:
        levels = vortex.get_multiple_detector_levels(list(range(1, 8)))
        pprint(levels)
        now = time()
        print('Time to read 8 detectors', now - t0)
        t0 = now


if __name__ == '__main__':
    main()
