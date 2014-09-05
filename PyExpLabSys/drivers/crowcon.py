"""This module contains a driver for the Vortex gas alarm central

.. seealso:: Docs for this implementation are on the wiki at:
    https://cinfwiki.fysik.dtu.dk/cinfwiki/Equipment#Vortex_Gas_Alarm_System
    or online at:
    http://www.crowcon.com/uk/products/control-panels/vortex.html

"""

from collections import namedtuple
import minimalmodbus


Status = namedtuple('Status', ['code', 'value'])
DetConfMap = namedtuple(
    'DetectorConfigurationMap',
    ['number', 'identity', 'enabled', 'type', 'unit', 'range',
     'level1', 'transition1', 'level2', 'transition2',
     'level3', 'transition3']
)
DetLev = namedtuple('DetectorLevels', ['number', 'level', 'status', 'inhibit'])


class Vortex(minimalmodbus.Instrument):
    """Driver for the Vortex gas alarm central

    .. note:: In the manual the register numbers are 1-based, but when sent
        to minimal modbus they need to be 0 based, either due to in-accurate
        manual or due to the implementaion in minimalmodbus.

    Args:
        serial_device (str): The serial device to use
        slave_address (int): The address of the slave device
    """

    def __init__(self, serial_device, slave_address, debug=False, cache=True):
        """Initialize the driver"""
        minimalmodbus.Instrument.__init__(self, serial_device,
                                          slave_address)
        self.serial.baudrate = 9600
        self.serial.stopbits = 2
        self.serial.timeout = 2.0
        # Variables
        self.debug = debug
        self.cache = cache
        # Cache
        self.system_conf = {}
        self.channel_conf = {}

    def close(self):
        """Close the connection"""
        self.serial.close()

    def read_bool(self, register):
        """Convert integer value to boolean"""
        integer = self.read_register(register)
        if integer == 0:  # Hex value 0000
            return False
        elif integer == 65535:  # Hex value FFFF
            return True
        else:
            raise ValueError('Only 0 or 65535 can be converted to a boolean')

    # System commands, manual section 4.5.1
    def get_type(self):
        """Get the device type"""
        return self.read_string(0, numberOfRegisters=8)

    def get_system_status_defunct(self):
        """Get the system status"""
        # Gives an integer 0 in standard mode, does not make sense with regards
        # to the map
        # Trying to set it to hold, also yields 0, so something is wrong
        return self.read_register(11)

    def get_system_power_status(self):
        """Get the system power status"""
        value = self.read_register(12)
        status = SYSTEM_POWER_STATUS.get(value, 'Unknown status value')
        return Status(value, status)

    def get_serial_number(self):
        """Get the serial number"""
        return self.read_string(32, numberOfRegisters=8)

    def get_system_name(self):
        """Get the serial number"""
        return self.read_string(33, numberOfRegisters=8)

    def get_number_installed_detectors(self):
        """Get the number of installed detector inputs"""
        if self.cache:
            if 'installed_detectors' not in self.system_conf:
                self.system_conf['installed_detectors'] = self.read_register(38)
            return self.system_conf['installed_detectors']
        else:
            return self.read_register(38)

    # pylint: disable=C0103
    def get_number_installed_digital_outputs(self):
        """Get the number of installed digital outputs"""
        return self.read_register(39)

    def detector_configuration(self, detector_number):
        """Read detector configuration

        Args:
            detector_number (int): The detector number. Detectors numbers are
            one based

        Returns:
            (DetConfMap): Named tuple containing the detector configuration
        """
        # Check for valid detector number
        num_detectors = self.get_number_installed_detectors()
        if detector_number not in range(1, num_detectors + 1):
            message = 'Only detector numbers 1-{} are valid'\
                .format(num_detectors)
            raise ValueError(message)

        # Return cached value if cache is True and it has been cached
        if self.cache and detector_number in self.channel_conf:
            return self.channel_conf[detector_number]

        # The registers for the detectors are shfited by 20 for each
        # register and the register numbers below are for detector 1
        reg_shift = 20 * (detector_number - 1)
        reg = {}
        reg['enabled']     = 109 + reg_shift
        reg['type']        = 110 + reg_shift
        reg['level1']      = 113 + reg_shift
        reg['transition1'] = 114 + reg_shift
        reg['level2']      = 115 + reg_shift
        reg['transition2'] = 116 + reg_shift
        reg['level3']      = 117 + reg_shift
        reg['transition3'] = 118 + reg_shift
        reg['unit']        = 121 + reg_shift
        reg['range']       = 122 + reg_shift
        reg['identity']    = 125 + reg_shift

        values = {'number': detector_number}
        # Read the identity string
        values['identity'] = self.read_string(reg['identity'],
                                              numberOfRegisters=4)
        values['identity'] = values['identity'].rstrip('\x00')
        # Read if the detector is enabled
        values['enabled'] = self.read_bool(reg['enabled'])
        # Read the detector type
        values['type'] = DETECTOR_TYPE.get(self.read_register(reg['type']),
                                           'Unknown Detector Type')
        # Read the units
        values['unit'] = UNITS.get(self.read_register(reg['unit']),
                                   'Unknown Unit')
        # Read the range and do not allow unknown range
        try:
            values['range'] = RANGE[self.read_register(reg['range'])]
        except KeyError:
            message = 'Unknown range code {}. Valid values are 9-25'
            raise ValueError(message)

        # Read alarm levels and transition types
        # Level 1
        values['level1'] = self.read_register(
            reg['level1'], numberOfDecimals=3, signed=True) * values['range']
        values['transition1'] = TRANSITION[self.read_bool(reg['transition1'])]
        # Level 2
        values['level2'] = self.read_register(
            reg['level2'], numberOfDecimals=3, signed=True) * values['range']
        values['transition2'] = TRANSITION[self.read_bool(reg['transition2'])]
        # Level 3
        values['level3'] = self.read_register(
            reg['level3'], numberOfDecimals=3, signed=True) * values['range']
        values['transition3'] = TRANSITION[self.read_bool(reg['transition3'])]

        # pylint: disable=W0142
        named_tuple_out = DetConfMap(**values)

        if self.cache:
            self.channel_conf[detector_number] = named_tuple_out

        return named_tuple_out

    def get_detector_levels(self, detector_number):
        """Read detector levels
        FIXME
        """
        # Check for valid detector number
        num_detectors = self.get_number_installed_detectors()
        if detector_number not in range(1, num_detectors + 1):
            message = 'Only detector numbers 1-{} are valid'\
                .format(num_detectors)
            raise ValueError(message)

        # The registers for the detectors are shfited by 10 for each
        # register and the register numbers below are for detector 1
        reg_shift = 10 * (detector_number - 1)

        # Get the range and read the level
        detector_range = self.detector_configuration(detector_number).range
        level = self.read_register(2999 + reg_shift, numberOfDecimals=3,
                                   signed=True) * detector_range

        status = self.read_register(3000 + reg_shift)
        status_out = []
        if status == 0:
            status_out.append('OK')
        else:
            bit_string = '{:016b}'.format(status)
            for key, value in DETECTOR_STATUS.items():
                if bit_string[key] == '1':
                    status_out.append(value)

        inhibited = self.read_bool(3003 + reg_shift)

        return DetLev(detector_number, level, status_out, inhibited)

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

# Units, section e.g. 4.5.2
UNITS = {
    0: '%LEL',
    1: '%VOL',
    2: 'PPM',
    3: 'Fire',
}

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
    9: 'Detector Inhibit from controller (inhibit button pushed or inhibited '
        'from comms link)',
}

#SYSTEM_STATUS = [
#    
#]
# BIT MEANING
# 0 Set to one if Vortex system is in channel test
# 1 Set to one if Vortex system is in jump hold
# 2 Set to one if Vortex system has a system fault.
# 3 Set to one if system fault is a battery fault.
# 4 Set to one if system fault is a FRAM data integrity
# fault
# 5 Set to one if system fault is an internal I2C bus fault.
# 6 Set to one if system fault is a display access fault.
# 7 Set to one if system fault is a power monitor access
# fault.
# 8 Set to one if system fault is an external I2C bus fault.
# 9 Set to one if system fault is a relay board fault.
