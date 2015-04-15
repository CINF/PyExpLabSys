# pylint: disable=too-many-lines,too-few-public-methods
# pylint: disable=too-many-lines,star-args,too-many-arguments,
# pylint: disable=too-many-public-methods,

"""This module is a Python implementation of a driver around the
EC-lib DLL. It can be used to control at least the SP-150 potentiostat
from Bio-Logic under 32 bit Windows.

.. toctree::
   :maxdepth: 2

.. note :: If it is desired to run this driver and the EC-lab development DLL
 on **Linux**, this can be **achieved with Wine**. This will require
 installing both the EC-lab development package AND Python inside
 Wine. Getting Python installed is easiest, if it is a 32 bit Wine
 environment, so before starting, it is recommended to set such an environment
 up. **NOTE:** In a cursory test, it appears that also EClab itself runs under
 Wine.

.. note :: When using the different techniques with the EC-lib DLL, different
 technique files must be passed to the library, depending on **which series
 the instrument is in (VMPW series or SP-300 series)**. However, the
 definition of which instruments are in which series was not clear from the
 specification, so instead it was copied from one of the examples. The
 definition used is that if the device id of your instrument (see
 :data:`DEVICE_CODES` for the full list of device ids) is in the
 :data:`SP300SERIES` list, then it is regarded as a SP-300 series device. If
 problems are encountered when loading the technique, then this might be the
 issues and it will posible be necessary to customize :data:`SP300SERIES`.

.. note :: On **64-bit Windows systems**, you should use the ``EClib64.dll``
 instead of the ``EClib.dll``. If the EC-lab development package is installed
 in the default location, this driver will try and load the correct DLL
 automatically, if not, the DLL path will need to passed explicitely and the
 user will need to take 32 vs. 64 bit into account. **NOTE:** The relevant 32
 vs. 64 bit status is that of Windows, not of Python.

.. note:: All methods mentioned in the documentation are implemented unless
 mentioned in the list below:

 * (General) BL_GetVolumeSerialNumber (Not implemented)
 * (Communications) BL_TestCommSpeed (Not implemented)
 * (Communications) BL_GetUSBdeviceinfos (Not implemented)
 * (Channel information) BL_GetHardConf (N/A, only available w. SP300 series)
 * (Channel information) BL_SetHardConf (N/A, only available w. SP300 series)
 * (Technique) BL_UpdateParameters (Not implemented)
 * (Start stop) BL_StartChannels (Not implemented)
 * (Start stop) BL_StopChannels (Not implemented)
 * (Data) BL_GetFCTData (Not implemented)
 * (Misc) BL_SetExperimentInfos (Not implemented)
 * (Misc) BL_GetExperimentInfos (Not implemented)
 * (Misc) BL_SendMsg (Not implemented)
 * (Misc) BL_LoadFlash (Not implemented)

"""

from __future__ import print_function
import os
import sys
import inspect
from collections import namedtuple
from ctypes import c_uint8, c_uint32, c_int32
from ctypes import c_float, c_double, c_char
from ctypes import Structure
from ctypes import create_string_buffer, byref, POINTER, cast
try:
    from ctypes import WinDLL
except ImportError:
    RUNNING_SPHINX = False
    for module in sys.modules:
        if 'sphinx' in module:
            RUNNING_SPHINX = True
    # Let the module continue after this fatal import error, if we are running
    # on read the docs or we can detect that sphinx is imported
    if not (os.environ.get('READTHEDOCS', None) == 'True' or RUNNING_SPHINX):
        raise

# Numpy is optional and is only required if it is resired to get the data as
# numpy arrays
try:
    import numpy
    GOT_NUMPY = True
except ImportError:
    GOT_NUMPY = False

# Conversion of data types:
# In doc    | ctypes
# ====================
# int8      | c_int8
# int16     | c_int16
# int32     | c_int32
# uint8     | c_uint8
# unit16    | c_uint16
# uint32    | c_uint32
# boolean   | c_uint8 (FALSE=0, TRUE=1)
# single    | c_float
# double    | c_double


### Named tuples

#:A named tuple used to defined a return data field for a technique
DataField = namedtuple(
    'DataField', ['name', 'type']
)
#:The TechniqueArgument instance, that are used as args arguments, are named
#:tuples with the following fields (in order):
#:
#: * label (str): the argument label mentioned in the :ref:`specification
#:   <specification>`
#: * type (str): the type used in the :ref:`specification <specification>`
#:   ('bool', 'single' and 'integer') and possibly wrap ``[]`` around to
#:   indicate an array e.g. ``[bool]```
#: * value: The value to be passed, will usually be forwarded from ``__init__``
#:   args
#: * check (str): The bounds check to perform (if any), possible values are
#:   '>=', 'in' and 'in_float_range'
#: * check_argument: The argument(s) for the bounds check. For 'in' should be a
#:   float or int, for 'in' should be a sequence and for 'in_float_range'
#:   should be a tuple of two floats
TechniqueArgument = namedtuple(
    'TechniqueArgument', ['label', 'type', 'value', 'check', 'check_argument']
)


########## Instrument classes
class GeneralPotentiostat(object):  # pylint: disable=too-many-public-methods
    """General driver for the potentiostats that can be controlled by the
    EC-lib DLL

    A driver for a specific potentiostat type will inherit from this class.

    Raises:
        ECLibError: All regular methods in this class use the EC-lib DLL
            communications library to talk with the equipment and they will
            raise this exception if this library reports an error. It will not
            be explicitly mentioned in every single method.
    """

    def __init__(self, type_, address, EClib_dll_path):
        """Initialize the potentiostat driver

        Args:
            type_ (str): The device type e.g. 'KBIO_DEV_SP150'
            address (str): The address of the instrument, either IP address or
                USB0, USB1 etc
            EClib_dll_path (str): The path to the EClib DLL. The default
                directory of the DLL is
                C:\\EC-Lab Development Package\\EC-Lab Development Package\\
                and the filename is either EClib64.dll or EClib.dll depending
                on whether the operating system is 64 of 32 Windows
                respectively. If no value is given the default location will be
                used and the 32/64 bit status inferred.

        Raises:
            WindowsError: If the EClib DLL cannot be found
        """
        self._type = type_
        if type_ in SP300SERIES:
            self.series = 'sp300'
        else:
            self.series = 'vmp3'

        self.address = address
        self._id = None
        self._device_info = None

        # Load the EClib dll
        if EClib_dll_path is None:
            EClib_dll_path = \
                'C:\\EC-Lab Development Package\\EC-Lab Development Package\\'

            # Appearently, this is the way to check whether this is 64 bit
            # Windows: http://stackoverflow.com/questions/2208828/
            # detect-64bit-os-windows-in-python. NOTE: That it is not
            # sufficient to use platform.architecture(), since that will return
            # the 32/64 bit value of Python NOT the OS
            if 'PROGRAMFILES(X86)' in os.environ:
                EClib_dll_path += 'EClib64.dll'
            else:
                EClib_dll_path += 'EClib.dll'

        self._eclib = WinDLL(EClib_dll_path)

    @property
    def id_number(self):  # pylint: disable=C0103
        """Return the device id as an int"""
        if self._id is None:
            return None
        return self._id.value

    @property
    def device_info(self):
        """Return the device information.

        Returns:
            dict or None: The device information as a dict or None if the
                device is not connected.
        """
        if self._device_info is not None:
            out = structure_to_dict(self._device_info)
            out['DeviceCode(translated)'] = DEVICE_CODES[out['DeviceCode']]
            return out

    # General functions
    def get_lib_version(self):
        """Return the version of the EClib communications library.

        Returns:
            str: The version string for the library
        """
        size = c_uint32(255)
        version = create_string_buffer(255)
        ret = self._eclib.BL_GetLibVersion(byref(version), byref(size))
        self.check_eclib_return_code(ret)
        return version.value

    def get_error_message(self, error_code):
        """Return the error message corresponding to error_code

        Args:
            error_code (int): The error number to translate

        Returns:
            str: The error message corresponding to error_code
        """
        message = create_string_buffer(255)
        number_of_chars = c_uint32(255)
        ret = self._eclib.BL_GetErrorMsg(
            error_code,
            byref(message),
            byref(number_of_chars)
        )
        # IMPORTANT, we cannot use, self.check_eclib_return_code here, since
        # that internally use this method, thus we have the potential for an
        # infinite loop
        if ret < 0:
            err_msg = 'The error message is unknown, because it is the '\
                      'method to retrieve the error message with that fails. '\
                      'See the error codes sections (5.4) of the EC-Lab '\
                      'development package documentation to get the meaning '\
                      'of the error code.'
            raise ECLibError(err_msg, ret)
        return message.value

    # Communications functions
    def connect(self, timeout=5):
        """Connect to the instrument and return the device info.

        Args:
            timeout (int): The connect timeout

        Returns:
            dict or None: The device information as a dict or None if the
                device is not connected.

        Raises:
            ECLibCustomException: If this class does not match the device type
        """
        address = create_string_buffer(self.address)
        self._id = c_int32()
        device_info = DeviceInfos()
        ret = self._eclib.BL_Connect(byref(address), timeout,
                                     byref(self._id),
                                     byref(device_info))
        self.check_eclib_return_code(ret)
        if DEVICE_CODES[device_info.DeviceCode] != self._type:
            message = 'The device type ({}) returned from the device '\
                      'on connect does not match the device type of '\
                      'the class ({})'.format(
                        DEVICE_CODES[device_info.DeviceCode],
                        self._type)
            raise ECLibCustomException(-9000, message)
        self._device_info = device_info
        return self.device_info

    def disconnect(self):
        """Disconnect from the device"""
        ret = self._eclib.BL_Disconnect(self._id)
        self.check_eclib_return_code(ret)
        self._id = None
        self._device_info = None

    def test_connection(self):
        """Test the connection"""
        ret = self._eclib.BL_TestConnection(self._id)
        self.check_eclib_return_code(ret)

    # Firmware functions
    def load_firmware(self, channels, force_reload=False):
        """Load the library firmware on the specified channels, if it is not
        already loaded

        Args:
            channels (list): List with 1 integer per channel (usually 16),
                (0=False and 1=True), that indicates which channels the
                firmware should be loaded on. NOTE: The length of the list must
                correspond to the number of channels supported by the
                equipment, not the number of channels installed. In most cases
                it will be 16.
            force_reload (bool): If True the firmware is forcefully reloaded,
                even if it was already loaded

        Returns:
            list: List of integers indicating the success of loading the
                firmware on the specified channel. 0 is success and negative
                values are errors, whose error message can be retrieved with
                the get_error_message method.
        """
        c_results = (c_int32 * len(channels))()
        p_results = cast(c_results, POINTER(c_int32))

        c_channels = (c_uint8 * len(channels))()
        for index in range(len(channels)):
            c_channels[index] = channels[index]
        p_channels = cast(c_channels, POINTER(c_uint8))

        ret = self._eclib.BL_LoadFirmware(
            self._id, p_channels, p_results, len(channels), False,
            force_reload, None, None)
        self.check_eclib_return_code(ret)
        return list(c_results)

    # Channel information functions
    def is_channel_plugged(self, channel):
        """Test if the selected channel is plugged.

        Args:
            channel (int): Selected channel (0-15 on most devices)

        Returns:
            bool: Whether the channel is plugged
        """
        result = self._eclib.BL_IsChannelPlugged(self._id, channel)
        return result == 1

    def get_channels_plugged(self):
        """Get information about which channels are plugged.

        Returns:
            (list): A list of channel plugged statusses as booleans
        """
        status = (c_uint8 * 16)()
        pstatus = cast(status, POINTER(c_uint8))
        ret = self._eclib.BL_GetChannelsPlugged(self._id, pstatus, 16)
        self.check_eclib_return_code(ret)
        return [result == 1 for result in status]

    def get_channel_infos(self, channel):
        """Get information about the specified channel.

        Args:
            channel (int): Selected channel, zero based (0-15 on most devices)

        Returns:
            dict: Channel infos dict. The dict is created by conversion from
                :class:`.ChannelInfos` class (type
                :py:class:`ctypes.Structure`). See the documentation for that
                class for a list of available dict items. Besides the items
                listed, there are extra items for all the original items whose
                value can be converted from an integer code to a string. The
                keys for those values are suffixed by (translated).
        """
        channel_info = ChannelInfos()
        self._eclib.BL_GetChannelInfos(self._id, channel,
                                       byref(channel_info))
        out = structure_to_dict(channel_info)

        # Translate code to strings
        out['FirmwareCode(translated)'] = \
            FIRMWARE_CODES[out['FirmwareCode']]
        out['AmpCode(translated)'] = AMP_CODES.get(out['AmpCode'])
        out['State(translated)'] = STATES.get(out['State'])
        out['MaxIRange(translated)'] = I_RANGES.get(out['MaxIRange'])
        out['MinIRange(translated)'] = I_RANGES.get(out['MinIRange'])
        out['MaxBandwidth'] = BANDWIDTHS.get(out['MaxBandwidth'])
        return out

    def get_message(self, channel):
        """ Return a message from the firmware of a channel """
        size = c_uint32(255)
        message = create_string_buffer(255)
        ret = self._eclib.BL_GetMessage(self._id, channel,
                                        byref(message),
                                        byref(size))
        self.check_eclib_return_code(ret)
        return message.value

    # Technique functions:
    def load_technique(self, channel, technique, first=True, last=True):
        """Load a technique on the specified channel

        Args:
            channel (int): The number of the channel to load the technique onto
            technique (Technique): The technique to load
            first (bool): Whether this technique is the first technique
            last (bool): Thether this technique is the last technique

        Raises:
            ECLibError: On errors from the EClib communications library
        """
        if self.series == 'sp300':
            filename, ext = os.path.splitext(technique.technique_filename)
            c_technique_file = create_string_buffer(filename + '4' + ext)
        else:
            c_technique_file = create_string_buffer(
                technique.technique_filename
            )

        # Init TECCParams
        c_tecc_params = TECCParams()
        # Get the array of parameter structs
        c_params = technique.c_args(self)
        # Set the len
        c_tecc_params.len = len(c_params)  # pylint:disable=W0201
        p_params = cast(c_params, POINTER(TECCParam))
        c_tecc_params.pParams = p_params  # pylint:disable=W0201,C0103

        ret = self._eclib.BL_LoadTechnique(
            self._id,
            channel,
            byref(c_technique_file),
            c_tecc_params,
            first,
            last,
            False,
        )
        self.check_eclib_return_code(ret)

    def define_bool_parameter(self, label, value, index, tecc_param):
        """Defines a boolean TECCParam for a technique

        This is a library convinience function to fill out the TECCParam struct
        in the correct way for a boolean value.

        Args:
            label (str): The label of the parameter
            value (bool): The boolean value for the parameter
            index (int): The index of the parameter
            tecc_param (TECCParam): An TECCParam struct
        """
        c_label = create_string_buffer(label)
        ret = self._eclib.BL_DefineBoolParameter(
            byref(c_label), value, index, byref(tecc_param)
        )
        self.check_eclib_return_code(ret)

    def define_single_parameter(self, label, value, index, tecc_param):
        """Defines a single (float) TECCParam for a technique

        This is a library convinience function to fill out the TECCParam struct
        in the correct way for a single (float) value.

        Args:
            label (str): The label of the parameter
            value (float): The float value for the parameter
            index (int): The index of the parameter
            tecc_param (TECCParam): An TECCParam struct
        """
        c_label = create_string_buffer(label)
        ret = self._eclib.BL_DefineSglParameter(
            byref(c_label), c_float(value), index, byref(tecc_param),
        )
        self.check_eclib_return_code(ret)

    def define_integer_parameter(self, label, value, index, tecc_param):
        """Defines an integer TECCParam for a technique

        This is a library convinience function to fill out the TECCParam struct
        in the correct way for a integer value.

        Args:
            label (str): The label of the parameter
            value (int): The integer value for the parameter
            index (int): The index of the parameter
            tecc_param (TECCParam): An TECCParam struct
        """
        c_label = create_string_buffer(label)
        ret = self._eclib.BL_DefineIntParameter(
            byref(c_label), value, index, byref(tecc_param)
        )
        self.check_eclib_return_code(ret)

    # Start/stop functions:
    def start_channel(self, channel):
        """Start the channel

        Args:
            channel (int): The channel number
        """
        ret = self._eclib.BL_StartChannel(self._id, channel)
        self.check_eclib_return_code(ret)

    def stop_channel(self, channel):
        """Stop the channel

        Args:
            channel (int): The channel number
        """
        ret = self._eclib.BL_StopChannel(self._id, channel)
        self.check_eclib_return_code(ret)

    # Data functions
    def get_current_values(self, channel):
        """Get the current values for the spcified channel

        Args:
            channel (int): The number of the channel (zero based)

        Returns:
            dict: A dict of current values information
        """
        current_values = CurrentValues()
        ret = self._eclib.BL_GetCurrentValues(
            self._id, channel, byref(current_values)
        )
        self.check_eclib_return_code(ret)

        # Convert the struct to a dict and translate a few values
        out = structure_to_dict(current_values)
        out['State(translated)'] = STATES[out['State']]
        out['IRange(translated)'] = I_RANGES[out['IRange']]
        return out

    def get_data(self, channel):
        """Get data for the specified channel

        Args:
            channel (int): The number of the channel (zero based)

        Returns:
            :class:`.KBIOData`: A :class:`.KBIOData` object or None if no data
                was available
        """
        # Raw data is retrieved in an array of integers
        c_databuffer = (c_uint32 * 1000)()
        p_data_buffer = cast(c_databuffer, POINTER(c_uint32))
        c_data_infos = DataInfos()
        c_current_values = CurrentValues()

        ret = self._eclib.BL_GetData(
            self._id,
            channel,
            p_data_buffer,
            byref(c_data_infos),
            byref(c_current_values),
        )
        self.check_eclib_return_code(ret)

        # The KBIOData will ask the appropriate techniques for which data
        # fields they return data in
        data = KBIOData(c_databuffer, c_data_infos, c_current_values, self)
        if data.technique == 'KBIO_TECHID_NONE':
            data = None

        return data

    def convert_numeric_into_single(self, numeric):
        """Convert a numeric (integer) into a float

        The buffer used to get data out of the device consist only of uint32s
        (most likely to keep its layout simple). To transfer a float, the
        EClib library uses a trick, wherein the value of the float is saved as
        a uint32, by giving the uint32 the integer values, whose
        bit-representation corresponds to the float that it should
        describe. This function is used to convert the integer back to the
        corresponding float.

        NOTE: This trick can also be performed with ctypes along the lines of:
        ``c_float.from_buffer(c_uint32(numeric))``, but in this driver the
        library version is used.

        Args:
            numeric (int): The integer that represents a float

        Returns:
            float: The float value

        """
        c_out_float = c_float()
        ret = self._eclib.BL_ConvertNumericIntoSingle(
            numeric,
            byref(c_out_float)
        )
        self.check_eclib_return_code(ret)
        return c_out_float.value

    def check_eclib_return_code(self, error_code):
        """Check a ECLib return code and raise the appropriate exception"""
        if error_code < 0:
            message = self.get_error_message(error_code)
            raise ECLibError(message, error_code)


class SP150(GeneralPotentiostat):
    """Specific driver for the SP-150 potentiostat"""

    def __init__(self, address, EClib_dll_path=None):
        """Initialize the SP150 potentiostat driver

        See the __init__ method for the GeneralPotentiostat class for an
        explanation of the arguments.
        """
        super(SP150, self).__init__(
            type_='KBIO_DEV_SP150',
            address=address,
            EClib_dll_path=EClib_dll_path
        )


########## Auxillary classes
class KBIOData(object):
    """Class used to represent data obtained with a get_data call

    The data can be obtained as lists of floats through attributes on this
    class. The time is always available through the 'time' attribute. The
    attribute names for the rest of the data, are the same as their names as
    listed in the field_names attribute. E.g:

    * kbio_data.Ewe
    * kbio_data.I

    Provided that numpy is installed, the data can also be obtained as numpy
    arrays by appending '_numpy' to the attribute name. E.g:

    * kbio_data.Ewe.numpy
    * kbio_data.I_numpy

    """

    def __init__(self, c_databuffer, c_data_infos, c_current_values,
                 instrument):
        """Initialize the KBIOData object

        Args:
            c_databuffer (Array of :py:class:`ctypes.c_uint32`): ctypes array
                of c_uint32 used as the data buffer
            c_data_infos (:class:`.DataInfos`): Data information structure
            c_current_values (:class:`CurrentValues`): Current values structure
            instrument (:class:`GeneralPotentiostat`): Instrument instance,
                should be an instance of a subclass of
                :class:`GeneralPotentiostat`

        Raises:
            ECLibCustomException: Where the error codes indicate the following:

                * -20000 means that the technique has no entry in
                  :data:`TECHNIQUE_IDENTIFIERS_TO_CLASS`
                * -20001 means that the technique class has no ``data_fields``
                  class variable
                * -20002 means that the ``data_fields`` class variables of the
                  technique does not contain the right information

        """
        technique_id = c_data_infos.TechniqueID
        self.technique = TECHNIQUE_IDENTIFIERS[technique_id]

        # Technique 0 means no data, get_data checks for this, so just return
        if technique_id == 0:
            return

        # Extract the process index, used to seperate data field classes for
        # techniques that support that, self.process = 1 also means no_time
        # variable in the beginning
        self.process = c_data_infos.ProcessIndex
        # Init the data_fields
        self.data_fields = self._init_data_fields(instrument)

        # Extract the number of points and columns
        self.number_of_points = c_data_infos.NbRaws
        self.number_of_columns = c_data_infos.NbCols
        self.starttime = c_data_infos.StartTime

        # Init time property, if the measurement process index indicates that
        # it has a special time variable
        if self.process == 0:
            self.time = []

        # Make lists for the data in properties named after the field_names
        for data_field in self.data_fields:
            setattr(self, data_field.name, [])

        # Parse the data
        self._parse_data(c_databuffer, c_current_values.TimeBase, instrument)

    def _init_data_fields(self, instrument):
        """Initialize the data fields property"""
        # Get the data_fields class variable from the corresponding technique
        # class
        if self.technique not in TECHNIQUE_IDENTIFIERS_TO_CLASS:
            message = \
                'The technique \'{}\' has no entry in '\
                'TECHNIQUE_IDENTIFIERS_TO_CLASS. The is required to be able '\
                'to interpret the data'.format(self.technique)
            raise ECLibCustomException(message, -20000)
        technique_class = TECHNIQUE_IDENTIFIERS_TO_CLASS[self.technique]

        if 'data_fields' not in technique_class.__dict__:
            message = 'The technique class {} does not defined a '\
                      '\'data_fields\' class variable, which is required for '\
                      'data interpretation.'.format(technique_class.__name__)
            raise ECLibCustomException(message, -20001)

        data_fields_complete = technique_class.data_fields
        if self.process == 1:  # Process 1 means no special time field
            try:
                data_fields_out = data_fields_complete['no_time']
            except KeyError:
                message = 'Unable to get data_fields from technique class. '\
                          'The data_fields class variable in the technique '\
                          'class must have either a \'no_time\' key when '\
                          'returning data with process index 1'
                raise ECLibCustomException(message, -20002)
        else:
            try:
                data_fields_out = data_fields_complete['common']
            except KeyError:
                try:
                    data_fields_out = data_fields_complete[instrument.series]
                except KeyError:
                    message =\
                        'Unable to get data_fields from technique class. '\
                        'The data_fields class variable in the technique '\
                        'class must have either a \'common\' or a \'{}\' '\
                        'key'.format(instrument.series)
                    raise ECLibCustomException(message, -20002)

        return data_fields_out

    def _parse_data(self, c_databuffer, timebase, instrument):
        """Parse the data

        Args:
            timebase (float): The timebase for the time calculation

        See :meth:`.__init__` for information about remaining args
        """
        # The data is written as one long array of points with a certain
        # amount of colums. Get the index of the first item of each point by
        # getting the range from 0 til n_point * n_columns in jumps of
        # n_columns
        for index in range(0, self.number_of_points * self.number_of_columns,
                           self.number_of_columns):
            # If there is a special time variable
            if self.process == 0:
                # Calculate the time
                t_high = c_databuffer[index]
                t_low = c_databuffer[index + 1]
                # NOTE: The documentation uses a bitshift operation for the:
                # ((t_high * 2 ** 32) + tlow) operation as
                # ((thigh << 32) + tlow), but I could not be bothered to
                # figure out exactly how a bitshift operation is defined for
                # an int class that can change internal representation, so I
                # just do the explicit multiplication
                self.time.append(
                    self.starttime +\
                    timebase * ((t_high * 2 ** 32) + t_low)
                )
                # Only offset reading the rest of the variables if there is a
                # special conversion time variable
                time_variable_offset = 2
            else:
                time_variable_offset = 0

            # Get remaining fields as defined in data fields
            for field_number, data_field in enumerate(self.data_fields):
                value = c_databuffer[index + time_variable_offset +
                                     field_number]
                # If the type is supposed to be float, convert the numeric to
                # float using the convinience function
                if data_field.type is c_float:
                    value = instrument.convert_numeric_into_single(value)

                # Append the field value to the appropriate list in a property
                getattr(self, data_field.name).append(value)

        # Check that the rest of the buffer is blank
        for index in range(self.number_of_points * self.number_of_columns,
                           1000):
            assert c_databuffer[index] == 0

    def __getattr__(self, key):
        """Return generated numpy arrays for the data instead of lists, if the
        requested property in on the form field_name + '_numpy'

        """
        # __getattr__ is only called after the check of whether the key is in
        # the instance dict, therefore it is ok to raise attribute error at
        # this points if the key does not have the special form we expect
        if key.endswith('_numpy'):
            # Get the requested field name e.g. Ewe
            requested_field = key.split('_numpy')[0]
            if requested_field in self.data_field_names or\
               requested_field == 'time':
                if GOT_NUMPY:
                    # Determin the numpy type to convert to
                    dtype = None
                    if requested_field == 'time':
                        dtype = float
                    else:
                        for field in self.data_fields:
                            if field.name == requested_field:
                                if field.type is c_float:
                                    dtype = float
                                elif field.type is c_uint32:
                                    dtype = int

                    if dtype is None:
                        message = 'Unable to infer the numpy data type for '\
                                  'requested field: {}'.format(requested_field)
                        raise ValueError(message)

                    # Convert the data and return the numpy array
                    return numpy.array(  # pylint: disable=no-member
                        getattr(self, requested_field),
                        dtype=dtype)
                else:
                    message = 'The numpy module is required to get the data '\
                              'as numpy arrays'
                    raise RuntimeError(message)

        message = '{} object has no attribute {}'.format(self.__class__, key)
        raise AttributeError(message)

    @property
    def data_field_names(self):
        """Return a list of extra data fields names (besides time)"""
        return [data_field.name for data_field in self.data_fields]


class Technique(object):
    """Base class for techniques

    All specific technique classes inherits from this class.

    Properties available on the object:

    * technique_filename (str): The name of the technique filename
    * args (tuple): Tuple containing the Python version of the
      parameters (see :meth:`.__init__` for details)
    * c_args (array of :class:`.TECCParam`): The c-types array of
      :class:`.TECCParam`

    A specific technique, that inherits from this class **must** overwrite the
    **data_fields** class variable. It describes what the form is, of the data
    that the technique can receive. The variable should be a dict on the
    following form:

    * Some techniques, like :class:`.OCV`, have different data fields depending
      on the series of the instrument. In these cases the dict must contain
      both a 'wmp3' and a 'sp300' key.
    * For cases where the instrument class distinction mentioned above does not
      exist, like e.g. for :class:`.CV`, one can simply define a 'common' key.
    * All three cases above assume that the first field of the returned data is
      a specially formatted ``time`` field, which must not be listed directly.
    * Some techniques, like e.g. :class:`.SPEIS` returns data for two different
      processes, one of which does not contain the ``time`` field (it is
      assumed that the process that contains ``time`` is 0 and the one that
      does not is 1). In this case there must be a 'common' and a 'no-time' key
      (see the implementation of :class:`.SPEIS` for details).

    All of the entries in the dict must point to an list of
    :class:`.DataField` named tuples, where the two arguments are the name and
    the C type of the field (usually :py:class:`c_float <ctypes.c_float>` or
    :py:class:`c_uint32 <ctypes.c_uint32>`). The list of fields must be in the
    order the data fields is specified in the :ref:`specification
    <specification>`.

    """

    data_fields = None

    def __init__(self, args, technique_filename):
        """Initialize a technique

        Args:
            args (tuple): Tuple of technique arguments as TechniqueArgument
                instances
            technique_filename (str): The name of the technique filename.

                .. note:: This must be the vmp3 series version i.e. name.ecc
                  NOT name4.ecc, the replacement of technique file names are
                  taken care of in load technique
        """
        self.args = args
        # The arguments must be converted to an array of TECCParam
        self._c_args = None
        self.technique_filename = technique_filename

    def c_args(self, instrument):
        """Return the arguments struct

        Args:
            instrument (:class:`GeneralPotentiostat`): Instrument instance,
                should be an instance of a subclass of
                :class:`GeneralPotentiostat`

        Returns:
            array of :class:`TECCParam`: An ctypes array of :class:`TECCParam`

        Raises:
            ECLibCustomException: Where the error codes indicate the following:

                * -10000 means that an :class:`TechniqueArgument` failed the
                  'in' test
                * -10001 means that an :class:`TechniqueArgument` failed the
                  '>=' test
                * -10002 means that an :class:`TechniqueArgument` failed the
                  'in_float_range' test
                * -10010 means that it was not possible to find a conversion
                  function for the defined type
                * -10011 means that the value cannot be converted with the
                  conversion function

        """
        if self._c_args is None:
            self._init_c_args(instrument)
        return self._c_args

    def _init_c_args(self, instrument):
        """Initialize the arguments struct

        Args:
            instrument (:class:`GeneralPotentiostat`): Instrument instance,
                should be an instance of a subclass of
                :class:`GeneralPotentiostat`
        """
        # If it is a technique that has multistep arguments, get the number of
        # steps
        step_number = 1
        for arg in self.args:
            if arg.label == 'Step_number':
                step_number = arg.value

        constructed_args = []
        for arg in self.args:
            # Bounds check the argument
            self._check_arg(arg)

            # When type is dict, it means that type is a int_code -> value_str
            # dict, that should be used to translate the str to an int by
            # reversing it be able to look up codes from strs and replace
            # value
            if isinstance(arg.type, dict):
                value = reverse_dict(arg.type)[arg.value]
                param = TECCParam()
                instrument.define_integer_parameter(arg.label, value, 0, param)
                constructed_args.append(param)
                continue

            # Get the appropriate conversion function, to populate the EccParam
            stripped_type = arg.type.strip('[]')
            try:
                # Get the conversion method from the instrument instance, this
                # is named something like defined_bool_parameter
                conversion_function = getattr(
                    instrument, 'define_{}_parameter'.format(stripped_type)
                )
            except AttributeError:
                message = 'Unable to find parameter definitions function for '\
                          'type: {}'.format(stripped_type)
                raise ECLibCustomException(message, -10010)

            # If the parameter is not a multistep paramter, put the value in a
            # list so we can iterate over it
            if arg.type.startswith('[') and arg.type.endswith(']'):
                values = arg.value
            else:
                values = [arg.value]

            # Iterate over all the steps for the parameter (for most will just
            # be 1)
            for index in range(min(step_number, len(values))):
                param = TECCParam()
                try:
                    conversion_function(arg.label, values[index], index, param)
                except ECLibError:
                    message = '{} is not a valid value for conversion to '\
                              'type {} for argument \'{}\''.format(
                                  values[index], stripped_type, arg.label)
                    raise ECLibCustomException(message, -10011)
                constructed_args.append(param)

        self._c_args = (TECCParam * len(constructed_args))()
        for index, param in enumerate(constructed_args):
            self._c_args[index] = param

    @staticmethod
    def _check_arg(arg):
        """Perform bounds check on a single argument"""
        if arg.check is None:
            return

        # If the type is not a dict (used for constants) and indicates an array
        elif not isinstance(arg.type, dict) and\
             arg.type.startswith('[') and arg.type.endswith(']'):
            values = arg.value
        else:
            values = [arg.value]

        # Check arguments with a list of accepted values
        if arg.check == 'in':
            for value in values:
                if value not in arg.check_argument:
                    message = '{} is not among the valid values for \'{}\'. '\
                              'Valid values are: {}'.format(
                                  value, arg.label, arg.check_argument)
                    raise ECLibCustomException(message, -10000)
            return

        # Perform bounds check, if any
        if arg.check == '>=':
            for value in values:
                if not value >= arg.check_argument:
                    message = 'Value {} for parameter \'{}\' failed '\
                              'check >={}'.format(
                                  value, arg.label, arg.check_argument)
                    raise ECLibCustomException(message, -10001)
            return

        # Perform in two parameter range check: A < value < B
        if arg.check == 'in_float_range':
            for value in values:
                if not arg.check_argument[0] <= value <= arg.check_argument[1]:
                    message = 'Value {} for parameter \'{}\' failed '\
                              'check between {} and {}'.format(
                                  value, arg.label,
                                  *arg.check_argument
                              )
                    raise ECLibCustomException(message, -10002)
            return

        message = 'Unknown technique parameter check: {}'.format(arg.check)
        raise ECLibCustomException(message, -10002)


# Section 7.2 in the specification
class OCV(Technique):
    """Open Circuit Voltage (OCV) technique class.

    The OCV technique returns data on fields (in order):

    * time (float)
    * Ewe (float)
    * Ece (float) (only wmp3 series hardware)
    """

    #: Data fields definition
    data_fields = {
        'vmp3': [DataField('Ewe', c_float), DataField('Ece', c_float)],
        'sp300': [DataField('Ewe', c_float)],
    }

    def __init__(self, rest_time_T=10.0, record_every_dE=10.0,
                 record_every_dT=0.1, E_range='KBIO_ERANGE_AUTO'):
        """Initialize the OCV technique

        Args:
            rest_time_t (float): The amount of time to rest (s)
            record_every_dE (float): Record every dE (V)
            record_every_dT  (float): Record evergy dT (s)
            E_range (str): A string describing the E range to use, see the
                :data:`E_RANGES` module variable for possible values
        """
        args = (
            TechniqueArgument('Rest_time_T', 'single', rest_time_T, '>=', 0),
            TechniqueArgument('Record_every_dE', 'single', record_every_dE,
                              '>=', 0),
            TechniqueArgument('Record_every_dT', 'single', record_every_dT,
                              '>=', 0),
            TechniqueArgument('E_Range', E_RANGES, E_range,
                              'in', E_RANGES.values()),
        )
        super(OCV, self).__init__(args, 'ocv.ecc')


# Section 7.3 in the specification
class CV(Technique):
    """Cyclic Voltammetry (CV) technique class.

    The CV technique returns data on fields (in order):

    * time (float)
    * Ec (float)
    * I (float)
    * Ewe (float)
    * cycle (int)
    """

    #:Data fields definition
    data_fields = {
        'common': [
            DataField('Ec', c_float),
            DataField('I', c_float),
            DataField('Ewe', c_float),
            DataField('cycle', c_uint32),
        ]
    }

    def __init__(self, vs_initial, voltage_step, scan_rate,
                 record_every_dE=0.1,
                 average_over_dE=True,
                 N_cycles=0,
                 begin_measuring_I=0.5,
                 end_measuring_I=1.0,
                 I_range='KBIO_IRANGE_AUTO',
                 E_range='KBIO_ERANGE_2_5',
                 bandwidth='KBIO_BW_5'
                 ):
        r"""Initialize the CV technique::

         E_we
         ^
         |       E_1
         |       /\
         |      /  \
         |     /    \      E_f
         | E_i/      \    /
         |            \  /
         |             \/
         |             E_2
         +----------------------> t

        Args:
            vs_initial (list): List (or tuple) of 5 booleans indicating
                whether the current step is vs. the initial one
            voltage_step (list): List (or tuple) of 5 floats (Ei, E1, E2, Ei,
                Ef) indicating the voltage steps (V)
            scan_rate (list): List (or tuple) of 5 floats indicating the scan
                rates (mV/s)
            record_every_dE (float): Record every dE (V)
            average_over_dE (bool): Whether averaging should be performed over
                dE
            N_cycles (int): The number of cycles
            begin_measuring_I (float): Begin step accumulation, 1 is 100%
            end_measuring_I (float): Begin step accumulation, 1 is 100%
            I_Range (str): A string describing the I range, see the
                :data:`I_RANGES` module variable for possible values
            E_range (str): A string describing the E range to use, see the
                :data:`E_RANGES` module variable for possible values
            Bandwidth (str): A string describing the bandwidth setting, see the
                :data:`BANDWIDTHS` module variable for possible values

        Raises:
            ValueError: If vs_initial, voltage_step and scan_rate are not all
                of length 5
        """
        for input_name in ('vs_initial', 'voltage_step', 'scan_rate'):
            if len(locals()[input_name]) != 5:
                message = 'Input \'{}\' must be of length 5, not {}'.format(
                    input_name, len(locals()[input_name]))
                raise ValueError(message)
        args = (
            TechniqueArgument('vs_initial', '[bool]', vs_initial,
                              'in', [True, False]),
            TechniqueArgument('Voltage_step', '[single]', voltage_step,
                              None, None),
            TechniqueArgument('Scan_Rate', '[single]', scan_rate, '>=', 0.0),
            TechniqueArgument('Scan_number', 'integer', 2, None, None),
            TechniqueArgument('Record_every_dE', 'single', record_every_dE,
                              '>=', 0.0),
            TechniqueArgument('Average_over_dE', 'bool', average_over_dE, 'in',
                              [True, False]),
            TechniqueArgument('N_Cycles', 'integer', N_cycles, '>=', 0),
            TechniqueArgument('Begin_measuring_I', 'single', begin_measuring_I,
                              'in_float_range', (0.0, 1.0)),
            TechniqueArgument('End_measuring_I', 'single', end_measuring_I,
                              'in_float_range', (0.0, 1.0)),
            TechniqueArgument('I_Range', I_RANGES, I_range,
                              'in', I_RANGES.values()),
            TechniqueArgument('E_Range', E_RANGES, E_range,
                              'in', E_RANGES.values()),
            TechniqueArgument('Bandwidth', BANDWIDTHS, bandwidth, 'in',
                              BANDWIDTHS.values()),
        )
        super(CV, self).__init__(args, 'cv.ecc')


# Section 7.4 in the specification
class CVA(Technique):
    """Cyclic Voltammetry Advanced (CVA) technique class.

    The CVA technique returns data on fields (in order):

    * time (float)
    * Ec (float)
    * I (float)
    * Ewe (float)
    * cycle (int)
    """

    #:Data fields definition
    data_fields = {
        'common': [
            DataField('Ec', c_float),
            DataField('I', c_float),
            DataField('Ewe', c_float),
            DataField('cycle', c_uint32),
        ]
    }

    def __init__(self,  # pylint: disable=too-many-locals
                 vs_initial_scan, voltage_scan, scan_rate,
                 vs_initial_step, voltage_step, duration_step,
                 record_every_dE=0.1,
                 average_over_dE=True,
                 N_cycles=0,
                 begin_measuring_I=0.5,
                 end_measuring_I=1.0,
                 record_every_dT=0.1,
                 record_every_dI=1,
                 trig_on_off=False,
                 I_range='KBIO_IRANGE_AUTO',
                 E_range='KBIO_ERANGE_2_5',
                 bandwidth='KBIO_BW_5'
                 ):
        r"""Initialize the CVA technique::

         E_we
         ^
         |       E_1
         |       /\
         |      /  \
         |     /    \   E_f_____________
         | E_i/      \    /<----------->|
         |            \  /      t_f     |_______E_i
         |             \/               |<----->
         |             E_2              |  t_i
         +------------------------------+-------------> t
                                        |
                                     trigger

        Args:
            vs_initial_scan (list): List (or tuple) of 4 booleans indicating
                whether the current scan is vs. the initial one
            voltage_scan (list): List (or tuple) of 4 floats (Ei, E1, E2, Ef)
                indicating the voltage steps (V) (see diagram above)
            scan_rate (list): List (or tuple) of 4 floats indicating the scan
                rates (mV/s)
            record_every_dE (float): Record every dE (V)
            average_over_dE (bool): Whether averaging should be performed over
                dE
            N_cycles (int): The number of cycles
            begin_measuring_I (float): Begin step accumulation, 1 is 100%
            end_measuring_I (float): Begin step accumulation, 1 is 100%
            vs_initial_step (list): A list (or tuple) of 2 booleans indicating
                whether this step is vs. the initial one
            voltage_step (list): A list (or tuple) of 2 floats indicating
                the voltage steps (V)
            duration_step (list): A list (or tuple) of 2 floats indicating
                the duration of each step (s)
            record_every_dT (float): A float indicating the change in time
                that leads to a point being recorded (s)
            record_every_dI (float): A float indicating the change in current
                that leads to a point being recorded (A)
            trig_on_off (bool): A boolean indicating whether to use the trigger
            I_Range (str): A string describing the I range, see the
                :data:`I_RANGES` module variable for possible values
            E_range (str): A string describing the E range to use, see the
                :data:`E_RANGES` module variable for possible values
            Bandwidth (str): A string describing the bandwidth setting, see the
                :data:`BANDWIDTHS` module variable for possible values

        Raises:
            ValueError: If vs_initial, voltage_step and scan_rate are not all
                of length 5
        """
        for input_name in ('vs_initial_scan', 'voltage_scan', 'scan_rate'):
            if len(locals()[input_name]) != 4:
                message = 'Input \'{}\' must be of length 4, not {}'.format(
                    input_name, len(locals()[input_name]))
                raise ValueError(message)

        for input_name in ('vs_initial_step', 'voltage_step', 'duration_step'):
            if len(locals()[input_name]) != 2:
                message = 'Input \'{}\' must be of length 2, not {}'.format(
                    input_name, len(locals()[input_name]))
                raise ValueError(message)

        args = (
            TechniqueArgument('vs_initial_scan', '[bool]', vs_initial_scan,
                              'in', [True, False]),
            TechniqueArgument('Voltage_scan', '[single]', voltage_scan,
                              None, None),
            TechniqueArgument('Scan_Rate', '[single]', scan_rate, '>=', 0.0),
            TechniqueArgument('Scan_number', 'integer', 2, None, None),
            TechniqueArgument('Record_every_dE', 'single', record_every_dE,
                              '>=', 0.0),
            TechniqueArgument('Average_over_dE', 'bool', average_over_dE, 'in',
                              [True, False]),
            TechniqueArgument('N_Cycles', 'integer', N_cycles, '>=', 0),
            TechniqueArgument('Begin_measuring_I', 'single', begin_measuring_I,
                              'in_float_range', (0.0, 1.0)),
            TechniqueArgument('End_measuring_I', 'single', end_measuring_I,
                              'in_float_range', (0.0, 1.0)),
            TechniqueArgument('vs_initial_step', '[bool]', vs_initial_step,
                              'in', [True, False]),
            TechniqueArgument('Voltage_step', '[single]', voltage_step,
                              None, None),
            TechniqueArgument('Duration_step', '[single]', duration_step,
                              None, None),
            TechniqueArgument('Step_number', 'integer', 1, None, None),
            TechniqueArgument('Record_every_dT', 'single', record_every_dT,
                              '>=', 0.0),
            TechniqueArgument('Record_every_dI', 'single', record_every_dI,
                              '>=', 0.0),
            TechniqueArgument('Trig_on_off', 'bool', trig_on_off,
                              'in', [True, False]),
            TechniqueArgument('I_Range', I_RANGES, I_range,
                              'in', I_RANGES.values()),
            TechniqueArgument('E_Range', E_RANGES, E_range,
                              'in', E_RANGES.values()),
            TechniqueArgument('Bandwidth', BANDWIDTHS, bandwidth, 'in',
                              BANDWIDTHS.values()),
        )
        super(CVA, self).__init__(args, 'biovscan.ecc')


# Section 7.5 in the specification
class CP(Technique):
    """Chrono-Potentiometry (CP) technique class.

    The CP technique returns data on fields (in order):

    * time (float)
    * Ewe (float)
    * I (float)
    * cycle (int)
    """

    #: Data fields definition
    data_fields = {
        'common': [
            DataField('Ewe', c_float),
            DataField('I', c_float),
            DataField('cycle', c_uint32),
        ]
    }

    def __init__(self, current_step=(50E-6,), vs_initial=(False,),
                 duration_step=(10.0,),
                 record_every_dT=0.1, record_every_dE=0.001,
                 N_cycles=0, I_range='KBIO_IRANGE_100uA',
                 E_range='KBIO_ERANGE_2_5', bandwidth='KBIO_BW_5'):
        """Initialize the CP technique

        NOTE: The current_step, vs_initial and duration_step must be a list or
        tuple with the same length.

        Args:
            current_step (list): List (or tuple) of floats indicating the
                current steps (A). See NOTE above.
            vs_initial (list): List (or tuple) of booleans indicating whether
                the current steps is vs. the initial one. See NOTE above.
            duration_step (list): List (or tuple) of floats indicating the
                duration of each step (s). See NOTE above.
            record_every_dT (float): Record every dT (s)
            record_every_dE (float): Record every dE (V)
            N_cycles (int): The number of times the technique is REPEATED.
                NOTE: This means that the default value is 0 which means that
                the technique will be run once.
            I_Range (str): A string describing the I range, see the
                :data:`I_RANGES` module variable for possible values
            E_range (str): A string describing the E range to use, see the
                :data:`E_RANGES` module variable for possible values
            Bandwidth (str): A string describing the bandwidth setting, see the
                :data:`BANDWIDTHS` module variable for possible values

        Raises:
            ValueError: On bad lengths for the list arguments
        """
        if not len(current_step) == len(vs_initial) == len(duration_step):
            message = 'The length of current_step, vs_initial and '\
                      'duration_step must be the same'
            raise ValueError(message)

        args = (
            TechniqueArgument('Current_step', '[single]', current_step,
                              None, None),
            TechniqueArgument('vs_initial', '[bool]', vs_initial,
                              'in', [True, False]),
            TechniqueArgument('Duration_step', '[single]', duration_step,
                              '>=', 0),
            TechniqueArgument('Step_number', 'integer', len(current_step),
                              'in', range(99)),
            TechniqueArgument('Record_every_dT', 'single', record_every_dT,
                              '>=', 0),
            TechniqueArgument('Record_every_dE', 'single', record_every_dE,
                              '>=', 0),
            TechniqueArgument('N_Cycles', 'integer', N_cycles, '>=', 0),
            TechniqueArgument('I_Range', I_RANGES, I_range,
                              'in', I_RANGES.values()),
            TechniqueArgument('E_Range', E_RANGES, E_range,
                              'in', E_RANGES.values()),
            TechniqueArgument('Bandwidth', BANDWIDTHS, bandwidth,
                              'in', BANDWIDTHS.values()),
        )
        super(CP, self).__init__(args, 'cp.ecc')


# Section 7.6 in the specification
class CA(Technique):
    """Chrono-Amperometry (CA) technique class.

    The CA technique returns data on fields (in order):

    * time (float)
    * Ewe (float)
    * I (float)
    * cycle (int)
    """

    #:Data fields definition
    data_fields = {
        'common': [DataField('Ewe', c_float),
                   DataField('I', c_float),
                   DataField('cycle', c_uint32)]
    }

    def __init__(self, voltage_step=(0.35,), vs_initial=(False,),
                 duration_step=(10.0,),
                 record_every_dT=0.1, record_every_dI=5E-6,
                 N_cycles=0, I_range='KBIO_IRANGE_AUTO',
                 E_range='KBIO_ERANGE_2_5', bandwidth='KBIO_BW_5'):
        """Initialize the CA technique

        NOTE: The voltage_step, vs_initial and duration_step must be a list or
        tuple with the same length.

        Args:
            voltage_step (list): List (or tuple) of floats indicating the
                voltage steps (A). See NOTE above.
            vs_initial (list): List (or tuple) of booleans indicating whether
                the current steps is vs. the initial one. See NOTE above.
            duration_step (list): List (or tuple) of floats indicating the
                duration of each step (s). See NOTE above.
            record_every_dT (float): Record every dT (s)
            record_every_dI (float): Record every dI (A)
            N_cycles (int): The number of times the technique is REPEATED.
                NOTE: This means that the default value is 0 which means that
                the technique will be run once.
            I_Range (str): A string describing the I range, see the
                :data:`I_RANGES` module variable for possible values
            E_range (str): A string describing the E range to use, see the
                :data:`E_RANGES` module variable for possible values
            Bandwidth (str): A string describing the bandwidth setting, see the
                :data:`BANDWIDTHS` module variable for possible values

        Raises:
            ValueError: On bad lengths for the list arguments
        """
        if not len(voltage_step) == len(vs_initial) == len(duration_step):
            message = 'The length of voltage_step, vs_initial and '\
                      'duration_step must be the same'
            raise ValueError(message)

        args = (
            TechniqueArgument('Voltage_step', '[single]', voltage_step,
                              None, None),
            TechniqueArgument('vs_initial', '[bool]', vs_initial,
                              'in', [True, False]),
            TechniqueArgument('Duration_step', '[single]', duration_step,
                              '>=', 0.0),
            TechniqueArgument('Step_number', 'integer', len(voltage_step),
                              'in', range(99)),
            TechniqueArgument('Record_every_dT', 'single', record_every_dT,
                              '>=', 0.0),
            TechniqueArgument('Record_every_dI', 'single', record_every_dI,
                              '>=', 0.0),
            TechniqueArgument('N_Cycles', 'integer', N_cycles, '>=', 0),
            TechniqueArgument('I_Range', I_RANGES, I_range,
                              'in', I_RANGES.values()),
            TechniqueArgument('E_Range', E_RANGES, E_range,
                              'in', E_RANGES.values()),
            TechniqueArgument('Bandwidth', BANDWIDTHS, bandwidth, 'in',
                              BANDWIDTHS.values()),
        )
        super(CA, self).__init__(args, 'ca.ecc')


# Section 7.12 in the specification
class SPEIS(Technique):
    """Staircase Potentio Electrochemical Impedance Spectroscopy (SPEIS)
    technique class

    The SPEIS technique returns data with a different set of fields depending
    on which process steps it is in. If it is in process step 0 it returns
    data on the following fields (in order):

    * time (float)
    * Ewe (float)
    * I (float)
    * step (int)

    If it is in process 1 it returns data on the following fields:

    * freq (float)
    * abs_Ewe (float)
    * abs_I (float)
    * Phase_Zwe (float)
    * Ewe (float)
    * I (float)
    * abs_Ece (float)
    * abs_Ice (float)
    * Phase_Zce (float)
    * Ece (float)
    * t (float)
    * Irange (float)
    * step (float)

    Which process it is in, can be checked with the ``process`` property on
    the :class:`.KBIOData` object.

    """

    #:Data fields definition
    data_fields = {
        'common': [
            DataField('Ewe', c_float),
            DataField('I', c_float),
            DataField('step', c_uint32),
        ],
        'no_time': [
            DataField('freq', c_float),
            DataField('abs_Ewe', c_float),
            DataField('abs_I', c_float),
            DataField('Phase_Zwe', c_float),
            DataField('Ewe', c_float),
            DataField('I', c_float),
            DataField('Blank0', c_float),
            DataField('abs_Ece', c_float),
            DataField('abs_Ice', c_float),
            DataField('Phase_Zce', c_float),
            DataField('Ece', c_float),
            DataField('Blank1', c_float),
            DataField('Blank2', c_float),
            DataField('t', c_float),
            # The manual says this is a float, but playing around with
            # strongly suggests that it is an uint corresponding to a I_RANGE
            DataField('Irange', c_uint32),
            # The manual does not mention data conversion for step, but says
            # that cycle should be an uint, however, this technique does not
            # have a cycle field, so I assume that it should have been the
            # step field. Also, the data maskes sense it you interpret it as
            # an uint.
            DataField('step', c_uint32),
        ]
    }

    def __init__(self,  # pylint: disable=too-many-locals
                 vs_initial, vs_final, initial_voltage_step,
                 final_voltage_step, duration_step, step_number,
                 record_every_dT=0.1, record_every_dI=5E-6,
                 final_frequency=100.0E3, initial_frequency=100.0,
                 sweep=True, amplitude_voltage=0.1,
                 frequency_number=1, average_n_times=1,
                 correction=False, wait_for_steady=1.0,
                 I_range='KBIO_IRANGE_AUTO',
                 E_range='KBIO_ERANGE_2_5', bandwidth='KBIO_BW_5'):
        """Initialize the SPEIS technique

        Args:
            vs_initial (bool): Whether the voltage step is vs. the initial one
            vs_final (bool): Whether the voltage step is vs. the final one
            initial_step_voltage (float): The initial step voltage (V)
            final_step_voltage (float): The final step voltage (V)
            duration_step (float): Duration of step (s)
            step_number (int): The number of voltage steps
            record_every_dT (float): Record every dT (s)
            record_every_dI (float): Record every dI (A)
            final_frequency (float): The final frequency (Hz)
            initial_frequency (float): The initial frequency (Hz)
            sweep (bool): Sweep linear/logarithmic (True for linear points
                spacing)
            amplitude_voltage (float): Amplitude of sinus (V)
            frequency_number (int): The number of frequencies
            average_n_times (int): The number of repeat times used for
                frequency averaging
            correction (bool): Non-stationary correction
            wait_for_steady (float): The number of periods to wait before each
                frequency
            I_Range (str): A string describing the I range, see the
                :data:`I_RANGES` module variable for possible values
            E_range (str): A string describing the E range to use, see the
                :data:`E_RANGES` module variable for possible values
            Bandwidth (str): A string describing the bandwidth setting, see the
                :data:`BANDWIDTHS` module variable for possible values

        Raises:
            ValueError: On bad lengths for the list arguments
        """
        args = (
            TechniqueArgument('vs_initial', 'bool', vs_initial,
                              'in', [True, False]),
            TechniqueArgument('vs_final', 'bool', vs_final,
                              'in', [True, False]),
            TechniqueArgument('Initial_Voltage_step', 'single',
                              initial_voltage_step, None, None),
            TechniqueArgument('Final_Voltage_step', 'single',
                              final_voltage_step, None, None),
            TechniqueArgument('Duration_step', 'single', duration_step,
                              None, None),
            TechniqueArgument('Step_number', 'integer', step_number,
                              'in', range(99)),
            TechniqueArgument('Record_every_dT', 'single', record_every_dT,
                              '>=', 0.0),
            TechniqueArgument('Record_every_dI', 'single', record_every_dI,
                              '>=', 0.0),
            TechniqueArgument('Final_frequency', 'single', final_frequency,
                              '>=', 0.0),
            TechniqueArgument('Initial_frequency', 'single', initial_frequency,
                              '>=', 0.0),
            TechniqueArgument('sweep', 'bool', sweep, 'in', [True, False]),
            TechniqueArgument('Amplitude_Voltage', 'single', amplitude_voltage,
                              None, None),
            TechniqueArgument('Frequency_number', 'integer', frequency_number,
                              '>=', 1),
            TechniqueArgument('Average_N_times', 'integer', average_n_times,
                              '>=', 1),
            TechniqueArgument('Correction', 'bool', correction,
                              'in', [True, False]),
            TechniqueArgument('Wait_for_steady', 'single', wait_for_steady,
                              '>=', 0.0),
            TechniqueArgument('I_Range', I_RANGES, I_range,
                              'in', I_RANGES.values()),
            TechniqueArgument('E_Range', E_RANGES, E_range,
                              'in', E_RANGES.values()),
            TechniqueArgument('Bandwidth', BANDWIDTHS, bandwidth, 'in',
                              BANDWIDTHS.values()),
        )
        super(SPEIS, self).__init__(args, 'seisp.ecc')


# Section 7.28 in the specification
class MIR(Technique):
    """Manual IR (MIR) technique class

    The MIR technique returns no data.
    """

    #:Data fields definition
    data_fields = {}

    def __init__(self, rcmp_value):
        """Initialize the MIR technique

        Args:
            rcmp_value (float): The R value to compensate
        """
        args = (
            TechniqueArgument('Rcmp_Value', 'single', rcmp_value, '>=', 0.0),
        )
        super(MIR, self).__init__(args, 'IRcmp.ecc')


########## Structs
class DeviceInfos(Structure):
    """Device information struct"""
    _fields_ = [  # Translated to string with DEVICE_CODES
                ('DeviceCode', c_int32),
                ('RAMsize', c_int32),
                ('CPU', c_int32),
                ('NumberOfChannels', c_int32),
                ('NumberOfSlots', c_int32),
                ('FirmwareVersion', c_int32),
                ('FirmwareDate_yyyy', c_int32),
                ('FirmwareDate_mm', c_int32),
                ('FirmwareDate_dd', c_int32),
                ('HTdisplayOn', c_int32),
                ('NbOfConnectedPC', c_int32)]

    # Hack to include the fields names in doc string (and Sphinx documentation)
    __doc__ += '\n\n    Fields:\n\n' + '\n'.join(
        ['    * {} {}'.format(*field) for field in _fields_]
    )


class ChannelInfos(Structure):
    """Channel information structure"""
    _fields_ = [
        ('Channel', c_int32),
        ('BoardVersion', c_int32),
        ('BoardSerialNumber', c_int32),
        # Translated to string with FIRMWARE_CODES
        ('FirmwareCode', c_int32),
        ('FirmwareVersion', c_int32),
        ('XilinxVersion', c_int32),
        # Translated to string with AMP_CODES
        ('AmpCode', c_int32),
        # NbAmp is not mentioned in the documentation, but is in
        # in the examples and the info does not make sense
        # without it
        ('NbAmp', c_int32),
        ('LCboard', c_int32),
        ('Zboard', c_int32),
        ('MUXboard', c_int32),
        ('GPRAboard', c_int32),
        ('MemSize', c_int32),
        ('MemFilled', c_int32),
        # Translated to string with STATES
        ('State', c_int32),
        # Translated to string with MAX_I_RANGES
        ('MaxIRange', c_int32),
        # Translated to string with MIN_I_RANGES
        ('MinIRange', c_int32),
        # Translated to string with MAX_BANDWIDTHS
        ('MaxBandwidth', c_int32),
        ('NbOfTechniques', c_int32),
    ]
    # Hack to include the fields names in doc string (and Sphinx documentation)
    __doc__ += '\n\n    Fields:\n\n' + '\n'.join(
        ['    * {} {}'.format(*field) for field in _fields_]
    )


class CurrentValues(Structure):
    """Current values structure"""
    _fields_ = [
        # Translate to string with STATES
        ('State', c_int32),  # Channel state
        ('MemFilled', c_int32),  # Memory filled (in Bytes)
        ('TimeBase', c_float),  # Time base (s)
        ('Ewe', c_float),  # Working electrode potential (V)
        ('EweRangeMin', c_float),  # Ewe min range (V)
        ('EweRangeMax', c_float),  # Ewe max range (V)
        ('Ece', c_float),  # Counter electrode potential (V)
        ('EceRangeMin', c_float),  # Ece min range (V)
        ('EceRangeMax', c_float),  # Ece max range (V)
        ('Eoverflow', c_int32),  # Potential overflow
        ('I', c_float),  # Current value (A)
        # Translate to string with IRANGE
        ('IRange', c_int32),  # Current range
        ('Ioverflow', c_int32),  # Current overflow
        ('ElapsedTime', c_float),  # Elapsed time
        ('Freq', c_float),  # Frequency (Hz)
        ('Rcomp', c_float),  # R-compenzation (Ohm)
        ('Saturation', c_int32),  # E or/and I saturation
    ]
    # Hack to include the fields names in doc string (and Sphinx documentation)
    __doc__ += '\n\n    Fields:\n\n' + '\n'.join(
        ['    * {} {}'.format(*field) for field in _fields_]
    )


class DataInfos(Structure):
    """DataInfos structure"""
    _fields_ = [
        ('IRQskipped', c_int32),  # Number of IRQ skipped
        ('NbRaws', c_int32),  # Number of raws into the data buffer,
                              # i.e. number of points saced in the
                              # data buffer
        ('NbCols', c_int32),  # Number of columns into the data
                              # buffer, i.e. number of variables
                              # defining a point in the data buffer
        ('TechniqueIndex', c_int32),  # Index (0-based) of the
                                      # technique that has generated
                                      # the data
        ('TechniqueID', c_int32),  # Identifier of the technique that
                                   # has generated the data
        ('ProcessIndex', c_int32),  # Index (0-based) of the process
                                    # of the technique that ahs
                                    # generated the data
        ('loop', c_int32),  # Loop number
        ('StartTime', c_double),  # Start time (s)
    ]
    # Hack to include the fields names in doc string (and Sphinx documentation)
    __doc__ += '\n\n    Fields:\n\n' + '\n'.join(
        ['    * {} {}'.format(*field) for field in _fields_]
    )


class TECCParam(Structure):
    """Technique parameter"""
    _fields_ = [
        ('ParamStr', c_char * 64),
        ('ParamType', c_int32),
        ('ParamVal', c_int32),
        ('ParamIndex', c_int32),
    ]
    # Hack to include the fields names in doc string (and Sphinx documentation)
    __doc__ += '\n\n    Fields:\n\n' + '\n'.join(
        ['    * {} {}'.format(*field) for field in _fields_]
    )


class TECCParams(Structure):
    """Technique parameters"""
    _fields_ = [
        ('len', c_int32),
        ('pParams', POINTER(TECCParam)),
    ]
    # Hack to include the fields names in doc string (and Sphinx documentation)
    __doc__ += '\n\n    Fields:\n\n' + '\n'.join(
        ['    * {} {}'.format(*field) for field in _fields_]
    )


########## Exceptions
class ECLibException(Exception):
    """Base exception for all ECLib exceptions"""
    def __init__(self, message, error_code):
        super(ECLibException, self).__init__(message)
        self.error_code = error_code

    def __str__(self):
        """__str__ representation of the ECLibException"""
        string = '{} code: {}. Message \'{}\''.format(
            self.__class__.__name__,
            self.error_code,
            self.message)
        return string

    def __repr__(self):
        """__repr__ representation of the ECLibException"""
        return self.__str__()


class ECLibError(ECLibException):
    """Exception for ECLib errors"""
    def __init__(self, message, error_code):
        super(ECLibError, self).__init__(message, error_code)


class ECLibCustomException(ECLibException):
    """Exceptions that does not originate from the lib"""
    def __init__(self, message, error_code):
        super(ECLibCustomException, self).__init__(message, error_code)


########## Functions
def structure_to_dict(structure):
    """Convert a ctypes.Structure to a dict"""
    out = {}
    for key, _ in structure._fields_:  # pylint: disable=protected-access
        out[key] = getattr(structure, key)
    return out


def reverse_dict(dict_):
    """Reverse the key/value status of a dict"""
    return dict([[v, k] for k, v in dict_.items()])


########## Constants
#:Device number to device name translation dict
DEVICE_CODES = {
    0: 'KBIO_DEV_VMP',
    1: 'KBIO_DEV_VMP2',
    2: 'KBIO_DEV_MPG',
    3: 'KBIO_DEV_BISTA',
    4: 'KBIO_DEV_MCS200',
    5: 'KBIO_DEV_VMP3',
    6: 'KBIO_DEV_VSP',
    7: 'KBIO_DEV_HCP803',
    8: 'KBIO_DEV_EPP400',
    9: 'KBIO_DEV_EPP4000',
    10: 'KBIO_DEV_BISTAT2',
    11: 'KBIO_DEV_FCT150S',
    12: 'KBIO_DEV_VMP300',
    13: 'KBIO_DEV_SP50',
    14: 'KBIO_DEV_SP150',
    15: 'KBIO_DEV_FCT50S',
    16: 'KBIO_DEV_SP300',
    17: 'KBIO_DEV_CLB500',
    18: 'KBIO_DEV_HCP1005',
    19: 'KBIO_DEV_CLB2000',
    20: 'KBIO_DEV_VSP300',
    21: 'KBIO_DEV_SP200',
    22: 'KBIO_DEV_MPG2',
    23: 'KBIO_DEV_SP100',
    24: 'KBIO_DEV_MOSLED',
    27: 'KBIO_DEV_SP240',
    255: 'KBIO_DEV_UNKNOWN'
}

#:Firmware number to firmware name translation dict
FIRMWARE_CODES = {
    0: 'KBIO_FIRM_NONE',
    1: 'KBIO_FIRM_INTERPR',
    4: 'KBIO_FIRM_UNKNOWN',
    5: 'KBIO_FIRM_KERNEL',
    8: 'KBIO_FIRM_INVALID',
    10: 'KBIO_FIRM_ECAL'
}

#:Amplifier number to aplifier name translation dict
AMP_CODES = {
    0: 'KBIO_AMPL_NONE',
    1: 'KBIO_AMPL_2A',
    2: 'KBIO_AMPL_1A',
    3: 'KBIO_AMPL_5A',
    4: 'KBIO_AMPL_10A',
    5: 'KBIO_AMPL_20A',
    6: 'KBIO_AMPL_HEUS',
    7: 'KBIO_AMPL_LC',
    8: 'KBIO_AMPL_80A',
    9: 'KBIO_AMPL_4AI',
    10: 'KBIO_AMPL_PAC',
    11: 'KBIO_AMPL_4AI_VSP',
    12: 'KBIO_AMPL_LC_VSP',
    13: 'KBIO_AMPL_UNDEF',
    14: 'KBIO_AMPL_MUIC',
    15: 'KBIO_AMPL_NONE_GIL',
    16: 'KBIO_AMPL_8AI',
    17: 'KBIO_AMPL_LB500',
    18: 'KBIO_AMPL_100A5V',
    19: 'KBIO_AMPL_LB2000',
    20: 'KBIO_AMPL_1A48V',
    21: 'KBIO_AMPL_4A10V'
}

#:I range number to I range name translation dict
I_RANGES = {
    0: 'KBIO_IRANGE_100pA',
    1: 'KBIO_IRANGE_1nA',
    2: 'KBIO_IRANGE_10nA',
    3: 'KBIO_IRANGE_100nA',
    4: 'KBIO_IRANGE_1uA',
    5: 'KBIO_IRANGE_10uA',
    6: 'KBIO_IRANGE_100uA',
    7: 'KBIO_IRANGE_1mA',
    8: 'KBIO_IRANGE_10mA',
    9: 'KBIO_IRANGE_100mA',
    10: 'KBIO_IRANGE_1A',
    11: 'KBIO_IRANGE_BOOSTER',
    12: 'KBIO_IRANGE_AUTO',
    13: 'KBIO_IRANGE_10pA',  # IRANGE_100pA + Igain x10
    14: 'KBIO_IRANGE_1pA',  # IRANGE_100pA + Igain x100
}

#:Bandwidth number to bandwidth name translation dict
BANDWIDTHS = {
    1: 'KBIO_BW_1',
    2: 'KBIO_BW_2',
    3: 'KBIO_BW_3',
    4: 'KBIO_BW_4',
    5: 'KBIO_BW_5',
    6: 'KBIO_BW_6',
    7: 'KBIO_BW_7',
    8: 'KBIO_BW_8',
    9: 'KBIO_BW_9'
}

#:E range number to E range name translation dict
E_RANGES = {
    0: 'KBIO_ERANGE_2_5',
    1: 'KBIO_ERANGE_5',
    2: 'KBIO_ERANGE_10',
    3: 'KBIO_ERANGE_AUTO'
}

#:State number to state name translation dict
STATES = {
    0: 'KBIO_STATE_STOP',
    1: 'KBIO_STATE_RUN',
    2: 'KBIO_STATE_PAUSE'
}

#:Technique number to technique name translation dict
TECHNIQUE_IDENTIFIERS = {
    0: 'KBIO_TECHID_NONE',
    100: 'KBIO_TECHID_OCV',
    101: 'KBIO_TECHID_CA',
    102: 'KBIO_TECHID_CP',
    103: 'KBIO_TECHID_CV',
    104: 'KBIO_TECHID_PEIS',
    105: 'KBIO_TECHID_POTPULSE',
    106: 'KBIO_TECHID_GALPULSE',
    107: 'KBIO_TECHID_GEIS',
    108: 'KBIO_TECHID_STACKPEIS_SLAVE',
    109: 'KBIO_TECHID_STACKPEIS',
    110: 'KBIO_TECHID_CPOWER',
    111: 'KBIO_TECHID_CLOAD',
    112: 'KBIO_TECHID_FCT',
    113: 'KBIO_TECHID_SPEIS',
    114: 'KBIO_TECHID_SGEIS',
    115: 'KBIO_TECHID_STACKPDYN',
    116: 'KBIO_TECHID_STACKPDYN_SLAVE',
    117: 'KBIO_TECHID_STACKGDYN',
    118: 'KBIO_TECHID_STACKGEIS_SLAVE',
    119: 'KBIO_TECHID_STACKGEIS',
    120: 'KBIO_TECHID_STACKGDYN_SLAVE',
    121: 'KBIO_TECHID_CPO',
    122: 'KBIO_TECHID_CGA',
    123: 'KBIO_TECHID_COKINE',
    124: 'KBIO_TECHID_PDYN',
    125: 'KBIO_TECHID_GDYN',
    126: 'KBIO_TECHID_CVA',
    127: 'KBIO_TECHID_DPV',
    128: 'KBIO_TECHID_SWV',
    129: 'KBIO_TECHID_NPV',
    130: 'KBIO_TECHID_RNPV',
    131: 'KBIO_TECHID_DNPV',
    132: 'KBIO_TECHID_DPA',
    133: 'KBIO_TECHID_EVT',
    134: 'KBIO_TECHID_LP',
    135: 'KBIO_TECHID_GC',
    136: 'KBIO_TECHID_CPP',
    137: 'KBIO_TECHID_PDP',
    138: 'KBIO_TECHID_PSP',
    139: 'KBIO_TECHID_ZRA',
    140: 'KBIO_TECHID_MIR',
    141: 'KBIO_TECHID_PZIR',
    142: 'KBIO_TECHID_GZIR',
    150: 'KBIO_TECHID_LOOP',
    151: 'KBIO_TECHID_TO',
    152: 'KBIO_TECHID_TI',
    153: 'KBIO_TECHID_TOS',
    155: 'KBIO_TECHID_CPLIMIT',
    156: 'KBIO_TECHID_GDYNLIMIT',
    157: 'KBIO_TECHID_CALIMIT',
    158: 'KBIO_TECHID_PDYNLIMIT',
    159: 'KBIO_TECHID_LASV',
    167: 'KBIO_TECHID_MP',
    169: 'KBIO_TECHID_CASG',
    170: 'KBIO_TECHID_CASP',
}

#:Technique name to technique class translation dict. IMPORTANT. Add newly
#:implemented techniques to this dictionary
TECHNIQUE_IDENTIFIERS_TO_CLASS = {
    'KBIO_TECHID_OCV': OCV,
    'KBIO_TECHID_CP': CP,
    'KBIO_TECHID_CA': CA,
    'KBIO_TECHID_CV': CV,
    'KBIO_TECHID_CVA': CVA,
    'KBIO_TECHID_SPEIS': SPEIS,
}

#:List of devices in the WMP4/SP300 series
SP300SERIES = [
    'KBIO_DEV_SP100', 'KBIO_DEV_SP200', 'KBIO_DEV_SP300', 'KBIO_DEV_VSP300',
    'KBIO_DEV_VMP300', 'KBIO_DEV_SP240'
]

# Hack to make links for classes in the documentation
__doc__ += '\n\nInstrument classes:\n'  # pylint: disable=W0622
for name, klass in inspect.getmembers(sys.modules[__name__], inspect.isclass):
    if issubclass(klass, GeneralPotentiostat) or klass is GeneralPotentiostat:
        __doc__ += ' * :class:`.{.__name__}`\n'.format(klass)

__doc__ += '\n\nTechniques:\n'
for name, klass in inspect.getmembers(sys.modules[__name__], inspect.isclass):
    if issubclass(klass, Technique):
        __doc__ += ' * :class:`.{.__name__}`\n'.format(klass)
