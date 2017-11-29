
"""Driver for the Epimax PVCi process vacuum controller

There are three controllers share the same kind of communication:

 * PVCX
 * PVCi
 * PVCiDuo

The structure of the communication to these devices is the same and a part of the
parameters are also the same, but there are also some parameters that differ. Therefore,
the driver is implemented in such a way, that there is a base class (PVCCommon) that
contains the communication functionality and the parameter from the common parameter
definition. There can then be one class for each of the 3 specific devices, that adds in
the parameters that are specific to this device. To see how that works, look at the
:py:class:`.PVCi` class.

The implementation in this file is based on the documents:

 * "EMComm MODBUS Communications Handbook" version 3.10
 * "PVCX, PVCi & PVCiDuo EMComm Parameter List Handbook" version 3.00 (hereafter referred
   to as the parameter list)

Unfortunately, these documents are not (that I could find) available on the web and must
be fetched by emailing `Epimax support <http://www.epimax.com/contact/contact.html>`_.

 .. note:: At present only the PVCi driver is implemented and only partially

 .. note:: At present no writing is implemented

"""

from __future__ import print_function, division
import sys
from struct import unpack
from functools import partial

# Note: At present this driver uses a modified version of minimalmodbus found here:
#
# https://github.com/CINF/minimalmodbus
#
# Which has initial support for functioncode 23 in read_string and read_float, which is
# necessary for this driver. It will be attempted for this to be mainlined, but it may
# take time.
import minimalmodbus

# This driver is Python 2 and 3, but you cannot use
#
# from __future__ import unicode_literals
#
# in the program running using it, since minimal modbus is missing a few corners in the
# conversion to Python 2 and 3 support
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


### Classes ###
###############

minimalmodbus.TIMEOUT = 1
minimalmodbus.FLOAT_ENDIANNESS = '<'
class PVCCommon(minimalmodbus.Instrument):
    """Common base for the PVCX, PVCi and PVCiDuo devices

    This common class must be sub-classed and the global_id and firmware_name class
    variables overwritten and the self.fields dict updated if necessary. See the
    :class:`.PVCi` inplementation for details.

    All requests for values (parameters) goes via value field names. To get a list of the
    available fields, have a look at the keys in the :attr:`.fields` dict of the common
    class and the sub-class. These fields names can then be used with :meth:`.get_field` and
    :meth:`.get_fields` method or accessed as if they were attributes of the class.

    Remember to call ``.close()`` after use.

    """

    # Must be overwritten in the subclasses
    global_id = None
    firmware_name = None

    def __init__(self, port, slave_address=1, check_hardware_version=True):
        """Initialize communication

        Args:
            port (unicode): The port specification of the device e.g. '/dev/????'
            slave_address (int): The address of the slave device, default is 1
            check_hardware_version (bool): Indicated whether a check should be performed
                for correct hardware at __init__ time
        """
        super(PVCCommon, self).__init__(
            port=port,
            slaveaddress=slave_address,
        )
        # fields is a the list of all the parameters that are common for all three types of
        # devices. It is a dict where keys are adapted parameter names and the values are
        # typles of (addres, type_or_type_convertion_function, unit)
        #
        # All values are assumed to be 4 bytes (2 registers) and convertion_function is the
        # function that converts those 4 bytes to the desired value.
        self.fields = {
            # Group 1
            'global_id': (0x00, 'string', None),
            'firmware_version': (0x02, bytes_to_firmware_version, None),
            # Group 2
            'unit_name': (0x10, 'string', None),
            'user_id': (0x12, 'string', None),
            # Group 5
            'slot_a_id': (0x42, bytes_to_slot_id, None),
            'slot_b_id': (0x44, bytes_to_slot_id, None),
            'bakeout_flags': (0x48, bytes_to_bakeout_flags, None),
            # Group 9
            'trip_1_7_status': (0x80, partial(bytes_to_status, status_type='trip'), None),
            'digital_input_1_2_status': (0x82,
                                         partial(bytes_to_status, status_type='digital_input'),
                                         None),
            # Group 10
            'ion_gauge_1_pressure': (0x9A, 'float', 'selected_unit'),
            # Group 14
            'bake_out_temp_1': (0xD0, 'float', 'C'),
            'bake_out_temp_2': (0xD2, 'float', 'C'),
            'bake_out_temp_3': (0xD4, 'float', 'C'),
            'bake_out_temp_4': (0xD6, 'float', 'C'),
            'bake_out_temp_5': (0xD8, 'float', 'C'),
            'bake_out_temp_6': (0xDA, 'float', 'C'),
            'bake_out_temp_hysteresis': (0xDC, 'float', 'C'),
            'ion_gauge_1_pressure_trip': (0xDE, 'float', 'selected_unit'),
            # Group 15
            'bake_out_time_1': (0xE0, 'float', 'h'),
            'bake_out_time_2': (0xE2, 'float', 'h'),
            'bake_out_time_3': (0xE4, 'float', 'h'),
            'bake_out_time_4': (0xE6, 'float', 'h'),
            'bake_out_time_5': (0xE8, 'float', 'h'),
            'bake_out_time_6': (0xEA, 'float', 'h'),
            'bake_out_setpoint': (0xEC, 'float', 'C'),
            'remaining_bake_out_time': (0xEE, 'float', 'h'),
        }

        if check_hardware_version:
            # Check that this is the correct hardware
            ids = self.get_fields(['global_id', 'firmware_version'])
            if ids['firmware_version'][0] != self.firmware_name or\
               ids['global_id'] != self.global_id:
                message = ('This driver class \'{}\' indicates that this hardware should '
                           'have global_id: \'{}\' and firmware name: \'{}\'. However, '
                           'the values are: \'{}\' and \'{}\'. This driver is not meant '
                           'for this hardware. To run anyway, set '
                           'check_hardware_version=False in __init__')
                raise ValueError(
                    message.format(
                        self.__class__.__name__, self.global_id, self.firmware_name,
                        ids['global_id'], ids['firmware_version'][0]
                    )
                )


    def close(self):
        """Close the serial connection"""
        self.serial.close()

    def _read_bytes(self, register_start, count=4):
        """Read and return `count` number of bytes starting from `register_start`

        Args:
            register_start (int): The register to start reading from
            count (int): The number of bytes to read (default 4)

        Returns:
            bytes: The read bytes
        """
        raw_value = self.read_string(
            registeraddress=register_start,
            numberOfRegisters=count//2,
            functioncode=23,
        )
        if sys.version_info.major >= 3:
            value = raw_value.encode('latin1')
        else:
            value = raw_value
        return value

    def get_field(self, field_name):
        """Return the value for the field named field_name

        Args:
            field_name (str): The name of the field to get. The names used are adapted
                parameter names from the command list turned. See the keys in
                :attr:`fields` to see all possible values.
        Returns:
            object: An object with type corresponding to the value (int, float or str)

        Raises:
            KeyError: If the requested field_name is unknown

        """
        address, type_or_convertion_function, _ = self.fields[field_name]
        if type_or_convertion_function == 'string':
            value = self.read_string(address, 2, 23)
        elif type_or_convertion_function == 'float':
            value = self.read_float(
                registeraddress=address,
                functioncode=23,
            )
        else:
            raw = self._read_bytes(address)
            value = type_or_convertion_function(raw)
        return value

    def get_fields(self, fields='common'):
        """Return a dict with fields and values for a list of fields

        This method is specifically for getting multiple values in the shortest
        amount of time. It works by always reading the maximum amount of registers (32)
        at a time and then using the remaining payload for subsequent values if they
        happen to be contained in the registers that have already been read.

        Args:
            fields (sequence or unicode): A sequence (list, tuple) of fields names or
                'common' which indicates fields with an address between 0x80 and 0x9E
                (this is the default) or 'all'.

        Returns:
            dict: Field name to value mapping
        """
        # Update and check fields
        if fields == 'common':
            # Form a list of the keys whose address is between 0x80 and 0x9E
            fields = [key for key, value in self.fields.items() if 0x80 <= value[0] <= 0x9E]
        elif fields == 'all':
            fields = self.fields.keys()
        else:
            for field in fields:
                if field not in self.fields:
                    message = 'Field name {} is not valid'.format(field)
                    raise KeyError(message)

        data = {field: self.get_field(field) for field in fields}
        return data

    def __getattr__(self, attrname):
        """Custom getattr implementation"""
        if attrname in self.fields:
            return self.get_field(attrname)
        else:
            message = '\'{}\' object has no attribute {}'.format(self.__class__.__name__,
                                                                 attrname)
            raise AttributeError(message)


class PVCi(PVCCommon):
    """Driver for the PVCi device

    For details of the functionality of this driver, see the docstring for the common base
    class :class:`PVCCommon`

    """

    # Used in the __init__ of PVCCommon to check for the correct hardware version
    global_id = 'PVCi'
    firmware_name = 'PVCi'

    def __init__(self, *args, **kwargs):
        """For specification for __init__ arguments, see :meth:`PVCCommon.__init__`"""

        super(PVCi, self).__init__(*args, **kwargs)
        # Update the common field definitions with those specific to the PVCi
        self.fields.update({
            'ion_gauge_1_status': (0x88,
                                   partial(ion_gauge_status, controller_type='pvci'),
                                   None),
            'slot_a_value_1': (0x90, 'float', None),
            'slot_a_value_2': (0x92, 'float', None),
            'slot_b_value_1': (0x94, 'float', None),
            'slot_b_value_2': (0x96, 'float', None),
        })


### Convertion Functions ###
############################

def bytes_to_firmware_version(bytes_):
    """Convert 4 bytes to firmware type and version"""
    # Reverse order
    bytes_ = bytes_[::-1]
    # The first two bytes identify the unit type (using UNIT_TYPE for conversion)
    if sys.version_info.major == 2:
        bytes_as_ints = [ord(n) for n in bytes_]
    else:
        bytes_as_ints = bytes_

    unit_code = tuple(bytes_as_ints[:2])
    unit_type = UNIT_TYPE[unit_code]

    # The last two are integer major and minor parts of the version
    version = '{}.{}'.format(*bytes_as_ints[2:])
    return unit_type, version


def bytes_to_string(bytes_, valid_chars=None):
    """Convert the 16 bit integer values from registers to a string

    Args:
        valid_chars (sequence): Sequence of two integers indicating the start and end of
            a range of valid bytes (both values included). All chars outside the range
            will be filtered out.
    """
    if valid_chars:
        bytes_ = b''.join(c for c in bytes_ if valid_chars[0] <= ord(c) <= valid_chars[1])
    return bytes_.decode('ascii')


def bytes_to_float(bytes_):
    """Convert 2 16 bit registers to a float"""
    return unpack('<f', bytes_)[0]


def bytes_to_slot_id(bytes_):
    """Convert 4 bytes to the slot ID"""

    id_byte = bytes_[::-1][3]
    raise_if_not_set(byte_to_bits(id_byte), 0, 'slot_id_a')
    try:
        id_int = ord(id_byte)
    except TypeError:
        id_int = id_byte

    slot_id = SLOT_IDS[id_int % 128]
    if slot_id == SLOT_IDS[5]:
        if ord(bytes_[::-1][1]) == 0:
            slot_id += ', log'
        else:
            slot_id += ', lin'
    return slot_id


def bytes_to_status(bytes_, status_type):
    """Convert bytes to trip and digital input statuses

    """
    # The 4 bits for a state is contained i 4 bytes, gather them up into one list
    all_states = []
    for byte_ in bytes_:
        bits_ = list(reversed(byte_to_bits(byte_)))
        all_states.extend([bits_[:4], bits_[4:]])

    # The 3 bit indicates whether status is used, sort out the rest
    all_states = [state for state in all_states if state[3]]

    states = {}
    for state_num, state_bits in enumerate(all_states, start=1):  # Enumeration starts at 1
        # Translate the state bits, if none is set, default to off
        if sum(state_bits[:3]) > 1:
            all_state_strings = []
            for bit_num, bit_meaning in enumerate(['on', 'inhibit', 'override']):
                if state_bits[bit_num]:
                    all_state_strings.append(bit_meaning)
            states[status_type + str(state_num)] = ', '.join(all_state_strings)
        else:
            states[status_type + str(state_num)] = 'off'

    return states


def byte_to_bits(byte, ):
    """Convert a byte to a list of bits"""
    try:
        byte_in = ord(byte)
    except TypeError:
        byte_in = byte
    bits = [b == '1' for b in bin(byte_in)[2:].zfill(8)]
    return bits


def raise_if_not_set(bits, index, parameter):
    """Raise a ValueError if bit is not set"""
    if not bits[index]:
        message = 'Bad \'{}\'. Expected bit {} to be set, got bits {}'
        raise ValueError(message.format(parameter, index, bits))


def ion_gauge_status(bytes_, controller_type=None):
    """Read of ion gauge status"""
    bytes_ = reversed(bytes_)
    status = {}

    # Ion gauge status
    bits = byte_to_bits(next(bytes_))
    for bit_, state in zip(bits, ALL_PVC_IONGAUGE_MODES):
        if bit_:
            status['status'] = state

    # Filemant type and number
    bits = byte_to_bits(next(bytes_))
    if controller_type == 'pvci':
        raise_if_not_set(bits, 0, 'filament type')
        status['filemant_type'] = 'tungsten' if bits[3] else 'iridium'
    raise_if_not_set(bits, 4, 'filemant number')
    status['filament_number'] = int(bits[7]) + 1

    # Measurement error and pressure trend
    bits = byte_to_bits(next(bytes_))
    raise_if_not_set(bits, 0, 'measurement error')
    status['measurement_error'] = 'electrometer input below min. limit' if bits[1] else 'none'

    raise_if_not_set(bits, 4, 'ion gauge trend')
    status['ion_gauge_trend'] = 'none'
    for bit_number, value in zip([7, 6], ['rising', 'falling']):
        if bits[bit_number]:
            status['ion_gauge_trend'] = value

    # Current ion gauge emission/degas setting
    if controller_type == 'pvci':
        byte = next(bytes_)
        bits = byte_to_bits(byte)
        raise_if_not_set(bits, 0, 'ion gauge emission/degas setting')
        status_dict = {'mode': 'manual'}
        for bit_number, value in zip([1, 3], ['autoemission', 'quick degas']):
            if bits[bit_number]:
                status_dict['mode'] = value

        # The current/power is given by an integer formed by the last 4 bits
        try:
            byte_as_int = ord(byte)
        except TypeError:
            byte_as_int = byte
        current_int = byte_as_int % 16
        status_dict['emission'] = PVCI_ION_GAUGE_STATUSSES[current_int]
        status['ion_gauge_emission_setting'] = status_dict
    else:
        raise NotImplementedError('Only controller type pvci is implement for gauge status')

    # Only return if there are no bytes left, else raise
    try:
        next(bytes_)
    except StopIteration:
        return status
    raise ValueError('Too many bytes for gauge status')


def bytes_to_bakeout_flags(bytes_):
    """Returns the bakeout flags from bytes"""
    bytes_ = reversed(bytes_)
    status = {}

    # Degas at end of bake
    bits = byte_to_bits(next(bytes_))
    status['degas_at_end_of_bake'] = bits[7]

    # Middle two bytes not implemented
    next(bytes_)
    next(bytes_)

    # Bakeout status
    bits = byte_to_bits(next(bytes_))
    status_flags = []
    for bit_number, flag in BAKEOUT_FLAGS.items():
        if bits[bit_number]:
            status_flags.append(flag)
    #if len(status_flags) == 0:
    #    status_flags.append('off')
    status['status_flags'] = status_flags

    return status


### Constants ###
#################

ALL_PVC_IONGAUGE_MODES = [
    'normal', 'fan_fail', 'digital_input_fail', 'over_pressure_fail',  # bits 0-3
    'emmision_failed', 'interlock_trip', 'emmission_trip',  # bits 4-6
    'filament_overcurrent_trip']  # bit 7


PVCI_ION_GAUGE_STATUSSES = {
    0x0: 'OFF',
    0x1: 'IGS_EM_100uA',
    0x2: 'IGS_EM_200uA',
    0x3: 'IGS_EM_500uA',
    0x4: 'IGS_EM_1mA',
    0x5: 'IGS_EM_2mA',
    0x6: 'IGS_EM_5mA',
    0x7: 'IGS_EM_10mA',
    0x8: 'IGS_EM_1W',
    0x9: 'IGS_EM_2W',
    0xA: 'IGS_EM_3W',
    0xB: 'IGS_EM_6W',
    0xC: 'IGS_EM_12W',
    0xD: 'IGS_EM_20W',
    0xE: 'IGS_EM_30W',
}


BAKEOUT_FLAGS = {
    7: 'bake-out started',
    6: 'bake-out is inhibited by assigned digital inputs',
    5: 'bake-out is inhibited by ion gauge pressure',
    4: 'bake-out is suspended',
    3: 'bake-out output is on',
}


UNIT_TYPE = {
    (0x45, 0x58): 'PVCX',
    (0x45, 0x44): 'PVCi',
    (0x45, 0x32): 'PVCiDuo',
}

SLOT_IDS = {
    0: 'empty',
    1: 'ion gauge (internally set)',
    2: 'V module, VG pirani gauge head',
    3: 'K module, type K thermocouple',
    4: 'E module, M and Thyracont Pirani gauge head',
    5: 'U module, universal input range',
}


### Quick test ###
##################
def run_module():
    """Tests basic functionality

    Will init a PVCi on USB0 and out all info fields and gauge 1 pressure and bakeout info
    continuously

    """
    import logging
    logging.basicConfig()
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    # '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTY3M2GN-if00-port0'
    #pvci = PVCi('/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTY3M2GN-if00-port0')
    pvci = PVCi('/dev/ttyUSB0')
    from pprint import pprint

    pprint(pvci.get_fields('all'))

    # Continuous
    try:
        while True:
            print(pvci.ion_gauge_1_status)
            for _ in range(20):
                print(
                    'Pressure {:.2e}  Setpoint: {:.2f}  Actual temp: {:.2f}'.format(
                        pvci.ion_gauge_1_pressure, pvci.bake_out_setpoint, pvci.slot_b_value_1
                    )
                )
    except KeyboardInterrupt:
        print('closing')


if __name__ == "__main__":
    run_module()
