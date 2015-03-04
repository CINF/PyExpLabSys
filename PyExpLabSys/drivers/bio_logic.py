# pylint: disable=R0903

""" This module is a Python wrapper for the EC-lib, that can be used to control
at least the SP-150 potentiostat from Bio-Logic. The main task of this module
is to wrap the Object Pascel (Delphi) DLL that is used to control the device.
"""

from ctypes import Structure, c_int
from ctypes import create_string_buffer, byref, WinDLL
from types import MethodType


# Dummy echo class
class EchoDll(object):
    """ Simple echo class """
    def __getattr__(self, function):
        def _dispatcher(self, *args):
            """ Generic echo method """
            print function, 'called with', list(args)
            return 0

        _dispatcher.__name__ = function
        method = MethodType(_dispatcher, self, self.__class__)
        setattr(self, function, method)
        return method


class SP150(object):
    """ Driver for the SP-150 potentiostat """

    def __init__(self, address=None):
        """ Address is the location of the instrument, either IP address or
        USB0, USB1 etc.
        """
        self.address = address
        self.eclib = WinDLL(ECLIB_DLL)
        self._id = None

    @property
    def id(self):  # pylint: disable=C0103
        """ Return the device id """
        if self._id is None:
            return None
        return self._id.value

    # General functions
    def get_lib_version(self):
        """ Return the version of the library """
        size = c_int(255)
        version = create_string_buffer(255)
        ret = self.eclib.BL_GetLibVersion(byref(version), byref(size))
        check_eclib_return_code(ret)
        return version.value

    # Communications functions
    def connect(self, timeout=5):
        """ Connect to the instrument """
        address = create_string_buffer(self.address)
        self._id = c_int()
        device_infos = DeviceInfos()
        ret = self.eclib.BL_Connect(byref(address), timeout, byref(self._id),
                                    byref(device_infos))
        check_eclib_return_code(ret)
        return device_infos


########## Structs
class DeviceInfos(Structure):
    """ Device information struct """
    _fields_ = [('DeviceCode', c_int),
                ('RAMsize', c_int),
                ('CPU', c_int),
                ('NumberOfChannels', c_int),
                ('NumberOfSlots', c_int),
                ('FirmwareVersion', c_int),
                ('FirmwareDate_yyyy', c_int),
                ('FirmwareDate_mm', c_int),
                ('FirmwareDate_dd', c_int),
                ('HTdisplayOn', c_int),
                ('NbOfConnectedPC', c_int)]


########## Exception
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


def main():
    """ Main method for tests """
    sp150 = SP150('130.225.86.97')
    print sp150.get_lib_version()
    global device_info
    device_info = sp150.connect()
    print device_info
    #t = ECLibError(-1)
    #print t

if __name__ == '__main__':
    main()
