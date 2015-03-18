# pylint: disable=R0903

""" This module is a Python wrapper for the EC-lib, that can be used to control
at least the SP-150 potentiostat from Bio-Logic. The main task of this module
is to wrap the Object Pascel (Delphi) DLL that is used to control the device.
"""

from ctypes import c_bool, c_uint8, c_uint32, c_int32, c_float, c_char
from ctypes import Structure
from ctypes import create_string_buffer, byref, WinDLL, POINTER, cast
from types import MethodType

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

########## Instrument classes
class GeneralPotentiostat(object):
    """ Driver for the SP-150 potentiostat

    Status of the implementation:
    General functions:
        BL_GetLibVersion (Implemented)
        BL_GetVolumeSerialNumber (Not implemented)
        BL_GetErrorMsg (Not needed*)
            * use module constant ERROR_CODES (type dict) instead
    Communications functions:
        BL_Connect (Implemented)
        BL_Disconnect (Implemented)
        BL_TestConnection (Implemented)
        BL_TestCommSpeed (Not implemented)
        BL_GetUSBdeviceinfos (Not implemented)
    Firmware functions:
        BL_LeadFirmware (Implemented)
    Channel Information functions:
        BL_IsChannelPlugged (Implemented)
        BL_GetChannelPlugged (Implemented)
        BL_GetChannelInfos (Implemented)
        BL_GetMessage (Implemented)
        BL_GetHardConf (N/A, only available w. SP300 series)
        BL_SetHardConf (N/A, only available w. SP300 series)
    Technique functions:
        BL_LoadTechnique (Not implemented)
        BL_LoadTechnique_LV (Not implemented, for Labview compatability)
        BL_LoadTechnique_VEE (Not implemented, for Vee Pro compat.)
        BL_DefineBoolParameter (Not implemented)
        BL_DefineSglParameter (Not implemented)
        BL_DefineIntParameter (Not implemented)
        BL_UpdateParameters (Not implemented)
        BL_UpdateParameters_LV (Not implemented, for Labview compat.)
        BL_UpdateParameters_VEE (Not implemented, for VeePro compat.)
    Start/stop functions:
        BL_StartChannel (Not implemented)
        BL_StartChannels (Not implemented)
        BL_StopChannel (Not implemented)
        BL_StopChannels (Not implemented)
    Data functions:
        BL_GetCurrentValues (Not implemented)
        BL_GetData (Not implemented)
        BL_GetFCTData (Not implemented)
        BL_GetDataVEE (Not implemented)
        BLConvertNumericIntoSingle (Not implemented)
    Miscellaneous functions:
        BL_SetExperimentInfos (Not implemented)
        BL_GetExperimentInfos (Not implemented)
        BL_SendMsg (Not implemented)
        BL_LoadFlash (Not implemented)
    """

    def __init__(self, address=None):
        """ Address is the location of the instrument, either IP address or
        USB0, USB1 etc.
        """
        self._type = ''
        self.address = address
        self._eclib = WinDLL(ECLIB_DLL)
        self._id = None
        self._device_info = None

    # Properties
    @property
    def id_number(self):  # pylint: disable=C0103
        """ Return the device id """
        if self._id is None:
            return None
        return self._id.value

    @property
    def device_info(self):
        """ Return the device info as a ctypes.Structure object with the
        following fields:
            DeviceCode, RAMsize, CPU, NumberOfChannels,
            NumberOfSlots, FirmwareVersion, FirmwareDate_yyyy,
            FirmwareDate_mm, FirmwareDate_dd, HTdisplayOn,
            NbOfConnectedPC

        Return None if the diver is not connected to the device.
        """
        out = structure_to_dict(self._device_info)
        out['DeviceCode(translated)'] = DEVICE_CODES[out['DeviceCode']]
        return out

    # General functions
    def get_lib_version(self):
        """ Return the version of the library """
        size = c_uint32(255)
        version = create_string_buffer(255)
        ret = self._eclib.BL_GetLibVersion(byref(version), byref(size))
        check_eclib_return_code(ret)
        return version.value

    # Communications functions
    def connect(self, timeout=5):
        """ Connect to the instrument and return the device info.
        
        Raise an ECLibError or ECLibCustomException on failure.
        """
        address = create_string_buffer(self.address)
        self._id = c_int32()
        device_info = DeviceInfos()
        ret = self._eclib.BL_Connect(byref(address), timeout,
                                     byref(self._id),
                                     byref(device_info))
        check_eclib_return_code(ret)
        if DEVICE_CODES[device_info.DeviceCode] != self._type:
            message = 'The device type ({}) returned from the device '\
                      'on connect does not match the device type of '\
                      'the class ({})'.format(
                        DEVICE_CODES[device_info.DeviceCode],
                        self._type)
            raise ECLibCustomException(-9000, message)
        self._device_info = device_info
        return

    def disconnect(self):
        """ Disconnect from the device. Raise ECLibError on errors. """
        ret = self._eclib.BL_Disconnect(self._id)
        check_eclib_return_code(ret)
        self._id = None
        self._device_info = None

    def test_connection(self):
        """ Test the connection. Raise ECLibError on errors. """
        ret = self._eclib.BL_TestConnection(self._id)
        check_eclib_return_code(ret)

    # Firmware functions
    def load_firmware(self, channels):
        """ Load the library firmware on the channels and return a list
        of statusses for the operation

        Arguments:
        channels    list with 1 element per channel (usually 16), where
                    0 (False) and 1 (True), that indicates which
                    channels the firmware should be loaded on. NOTE the
                    length of the list must correspond to the number of
                    channels supported by the equipment, not the number
                    installed. In most cases it will be 16.
        
        Raise ECLibError on error.
        """
        c_results = (c_int32 * len(channels))()
        p_results = cast(c_results, POINTER(c_int32))

        c_channels = (c_uint8 * len(channels))()
        for index, value in enumerate(channels):
            c_channels[index] = channels[index]
        p_channels = cast(c_channels, POINTER(c_uint8))

        self._eclib.BL_LoadFirmware(self._id, p_channels, c_results,
                                    len(channels), True, False, None, None)
        return list(c_results)

    # Channel information functions
    def is_channel_plugged(self, channel):
        """ Test if the selected channel is plugged.
        
        Arguments:
        channel:    selected channel (0-15)
        
        Raise ECLibError on errors.
        """
        result = self._eclib.BL_IsChannelPlugged(self._id, channel)
        result = True if result == 1 else False
        return result

    def get_channels_plugged(self):
        """ Return a list that describes what channels are plugged.
        
        Raise ECLibError on errors. """
        status = (c_uint8 * 16)()
        pstatus = cast(status, POINTER(c_uint8))
        ret = self._eclib.BL_GetChannelsPlugged(self._id, pstatus, 16)
        check_eclib_return_code(ret)
        return list(status)

    def get_channel_infos(self, channel):
        """ Return channel information.
        
        Raise ECLibError on errors.
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
        out['MaxIRange(translated)'] = IRANGES.get(out['MaxIRange'])
        out['MinIRange(translated)'] = IRANGES.get(out['MinIRange'])
        out['MaxBandwidth'] = BANDWIDTHS.get(out['MaxBandwidth'])
        return out

    def get_message(self, channel):
        """ Return a message from the firmware of a channel """
        size = c_uint32(255)
        message = create_string_buffer(255)
        ret = self._eclib.BL_GetMessage(self._id, channel,
                                        byref(message),
                                        byref(size))
        check_eclib_return_code(ret)
        return message.value

    # Technique functions:
    def load_technique(self, technique):
        """ ????? """
        pass


class SP150(GeneralPotentiostat):
    """ Specific driver for the SP-150 potentiostat """
    def __init__(self, address):
        super(SP150, self).__init__(address)
        self._type = 'KBIO_DEV_SP150'


########## Auxillary classes
class Technique(object):
    """ Abstract technique class. All specific technique classes
    inherits from this class.
    """
    def __init__(self, args, technique_filename):
        self.args = args
        self._c_args = []
        self._technique_filename = technique_filename
        self._test_args()
        self._init_args()
        

    @property
    def technique_filename(self):
        """ Return the technique name """
        return self._technique_filename

    def _test_args(self):
        """ Test types of the given arguments """
        for key, value in self.args.items():
            if type(value[0]) is dict:
                if value[1] not in value[0].values():
                    message = '{} is not among the valid values for '\
                        '{}'.format(value[1], key)
                    raise(ECLibCustomException(-10000, message))
            else:
                try:
                    value[0](value[1])
                except TypeError:
                    message = '{} is not a valid value for conversion '\
                        'to type {} for argument {}'.format(value[1],
                                                            value[0],
                                                            key)
                    raise(ECLibCustomException(-10001, message))

    def _init_args(self):
        """ Initialize the argument structs """
        for key, value in self.args.items():
            param = TECCParam()
            param.ParamStr = key
            if type(value[0]) is dict:
                # The type is always 0 = int for 
                param.ParamType = 0
                # Convert the constant name e.g. 'KBIO_ERANGE_AUTO' to
                # its integer representation e.g. 3
                val = reverse_dict(value[0])[value[1]]
                param.ParamVal = val
            elif value[0] is c_int32:
                # The type for a c_int32 is 0
                param.ParamType = 1
                # Is already an int
                param.ParamVal = value[1]
            elif value[0] is c_bool:
                # The type for a c_bool is 1
                param.ParamType = 1
                # For bools False=0, True = 1
                param.ParamVal = 1 if value[1] else 0
            elif value[0] is c_float:
                # The type for a c_float is 2
                param.ParamType = 2
                # The value written is the integer that has the same
                # binary presentation as the float !!!
                param.ParamVal = c_int32.from_buffer(c_float(value[1]))
            self._c_args.append(param)
        print self._c_args

    def print_param(param):
        pass

class OCV(Technique):
    """ OCV technique class """
    def __init__(self, Rest_time_T=0.0, Record_every_dE=0.1,
                 Record_every_dT=0.1, E_Range='KBIO_ERANGE_AUTO'):
        """ Initialize the OCV technique """
        args = {'Rest_time_T': (c_float, Rest_time_T),
                'Record_every_dE': (c_float, Record_every_dE),
                'Record_every_dT': (c_float, Record_every_dT),
                'E_Range': (E_RANGE, E_Range)}
        super(OCV, self).__init__(args, 'ocv.ecc')


########## Structs
class DeviceInfos(Structure):
    """ Device information struct """
    _fields_ = [# Translated to string with DEVICE_CODES
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


class ChannelInfos(Structure):
    """ Channel information structure """
    _fields_ = [('Channel', c_int32),
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
                # Translated to string with MAX_IRANGES
                ('MaxIRange', c_int32),
                # Translated to string with MIN_IRANGES
                ('MinIRange', c_int32),
                # Translated to string with MAX_BANDWIDTHS
                ('MaxBandwidth', c_int32),
                ('NbOfTechniques', c_int32)]


class TECCParam(Structure):
    """ Technique parameter """
    _fields_ = [('ParamStr', c_char * 64),
                ('ParamType', c_int32),
                ('ParamVal', c_int32),
                ('ParamIndex', c_int32)]


########## Exceptions
class ECLibException(Exception):
    """ Base exception for all ECLib exceptions """
    def __init__(self, error_code):
        super(ECLibException, self).__init__()
        self.error_code = error_code
        self.message = ''

    def __str__(self):
        """ str representation of the ECLibException """
        string = '{} code: {} of type \'{}\''.format(
            self.__class__.__name__,
            self.error_code,
            self.message)
        return string

    def __repr__(self):
        """ repr representation of the ECLibException """
        return self.__str__()


class ECLibError(ECLibException):
    """ Exception for ECLib errors.

    The middle part of self.message informs about the type of message
    i.e: GEN for general, INSTR for instrument, COMM for communication,
    FIRM for firmware and TECH for technique
    """
    def __init__(self, error_code):
        super(ECLibError, self).__init__(error_code)
        self.message = ERROR_CODES[error_code]


class ECLibCustomException(ECLibException):
    """ Exceptions that does not originate from the lib """
    def __init__(self, error_code, message):
        super(ECLibCustomException, self).__init__(error_code)
        self.message = message


########## Functions
def check_eclib_return_code(error_code):
    """ Check a ECLib return code and raise the appropriate exception """
    if error_code < 0:
        raise ECLibError(error_code)

def structure_to_dict(structure):
    """ Convert a ctypes.Structure to a dict """
    out = {}
    for key, _ in structure._fields_:
        out[key] = getattr(structure, key)
    return out

def reverse_dict(dict_):
    """ Reverse the key/value status of a dict """
    return dict([[v, k] for k, v in dict_.items()])

########## Constants
ECLIB_DLL = 'C:\EC-Lab Development Package\EC-Lab Development Package/EClib.dll'

NB_CH = 16

ERROR_CODES = {
    0: 'ERR_NOERROR',
    # General error codes
    -1: 'ERR_GEN_NOTCONNECTED',
    -2: 'ERR_GEN_CONNECTIONINPROGRESS',
    -3: 'ERR_GEN_CHANNELNOTPLUGGED',
    -4: 'ERR_GEN_INVALIDPARAMETERS',
    -5: 'ERR_GEN_FILENOTEXISTS',
    -6: 'ERR_GEN_FUNCTIONFAILED',
    -7: 'ERR_GEN_NOCHANNELSELECTED',
    -8: 'ERR_GEN_INVALIDCONF',
    -9: 'ERR_GEN_ECLAB_LOADED',
    -10: 'ERR_GEN_LIBNOTCORRECTLYLOADED',
    -11: 'ERR_GEN_USBLIBRARYERROR',
    -12: 'ERR_GEN_FUNCTIONINPROGRESS',
    -13: 'ERR_GEN_CHANNEL_RUNNING',
    -14: 'ERR_GEN_DEVICE_NOTALLOWED',
    -15: 'ERR_GEN_UPDATEPARAMETERS',
    # Instrument error codes
    -101: 'ERR_INSTR_VMEERROR',
    -102: 'ERR_INSTR_TOOMANYDATA',
    -103: 'ERR_INSTR_RESPNOTPOSSIBLE',
    -104: 'ERR_INSTR_RESPERROR',
    -105: 'ERR_INSTR_MSGSIZEERROR',
    # Communication error code
    -200: 'ERR_COMM_COMMFAILED',
    -201: 'ERR_COMM_CONNECTIONFAILED',
    -202: 'ERR_COMM_WAITINGACK',
    -203: 'ERR_COMM_INVALIDIPADDRESS',
    -204: 'ERR_COMM_ALLOCMEMFAILED',
    -205: 'ERR_COMM_LOADFIRMWAREFAILED',
    -206: 'ERR_COMM_INCOMPATIBLESERVER',
    -207: 'ERR_COMM_MAXCONNREACHED',
    # Firmware error codes
    -300: 'ERR_FIRM_FIRMFILENOTEXISTS',
    -301: 'ERR_FIRM_FIRMFILEACCESSFAILED',
    -302: 'ERR_FIRM_FIRMINVALIDFILE',
    -303: 'ERR_FIRM_FIRMLOADINGFAILED',
    -304: 'ERR_FIRM_XILFILENOTEXISTS',
    -305: 'ERR_FIRM_XILFILEACCESSFAILED',
    -306: 'ERR_FIRM_XILINVALIDFILE',
    -307: 'ERR_FIRM_XILLOADINGFAILED',
    -308: 'ERR_FIRM_FIRMWARENOTLOADED',
    -309: 'ERR_FIRM_FIRMWAREINCOMPATIBLE',
    # Technical error codes
    -400: 'ERR_TECH_ECCFILENOTEXISTS',
    -401: 'ERR_TECH_INCOMPATIBLEECC',
    -402: 'ERR_TECH_ECCFILECORRUPTED',
    -403: 'ERR_TECH_LOADTECHNIQUEFAILED',
    -404: 'ERR_TECH_DATACORRUPTED',
    -405: 'ERR_TECH_MEMFULL'
}

DEVICE_CODES = {
    0: 'KBIO_DEV_VMP',
    1: 'KBIO_DEV_VMP2',
    2: 'KBIO_DEV_MPG',
    3: 'KBIO_DEV_BISTAT',
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

FIRMWARE_CODES = {
    0: 'KBIO_FIRM_NONE',
    1: 'KBIO_FIRM_INTERPR',
    4: 'KBIO_FIRM_UNKNOWN',
    5: 'KBIO_FIRM_KERNEL',
    8: 'KBIO_FIRM_INVALID',
    10: 'KBIO_FIRM_ECAL'
}

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

IRANGES = {
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
    13: 'KBIO_IRANGE_10pA', # IRANGE_100pA + Igain x10
    14: 'KBIO_IRANGE_1pA' # IRANGE_100pA + Igain x100
}

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

STATES = {
    0: 'KBIO_STATE_STOP',
    1: 'KBIO_STATE_RUN',
    2: 'KBIO_STATE_PAUSE'
}

E_RANGE = {
    0: 'KBIO_ERANGE_2_5',
    1: 'KBIO_ERANGE_5',
    2: 'KBIO_ERANGE_10',
    3: 'KBIO_ERANGE_AUTO'
}
