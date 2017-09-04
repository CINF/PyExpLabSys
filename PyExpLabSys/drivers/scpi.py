""" Implementation of SCPI standard """
from __future__ import print_function
import time
import logging
import telnetlib
import serial
try:
    import usbtmc
except ImportError:
    usbtmc = None
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
LOGGER.addHandler(logging.NullHandler())


class SCPI(object):
    """ Driver for scpi communication """
    def __init__(self, interface, device='', tcp_port=5025, hostname='', baudrate=9600,
                 visa_string='', line_ending='\r'):
        self.device = device
        self.line_ending = line_ending
        self.interface = interface
        if self.interface == 'file':
            self.comm_dev = open(self.device, 'w')
            self.comm_dev.close()
        if self.interface == 'serial':
            self.comm_dev = serial.Serial(self.device, baudrate, timeout=2, xonxoff=True)
        if self.interface == 'lan':
            self.comm_dev = telnetlib.Telnet(hostname, tcp_port)
        if self.interface == 'usbtmc':
            if usbtmc is None:
                exit('usbtmc is not availalbe')
            self.comm_dev = usbtmc.Instrument(visa_string)


    def scpi_comm(self, command, expect_return=False):
        """ Implements actual communication with SCPI instrument """
        return_string = ""
        if self.interface == 'file':
            self.comm_dev = open(self.device, 'w')
            self.comm_dev.write(command)
            time.sleep(0.02)
            self.comm_dev.close()
            time.sleep(0.05)
            if command.find('?') > -1:
                self.comm_dev = open(self.device, 'r')
                return_string = self.comm_dev.readline()
                self.comm_dev.close()
        command_text = command + self.line_ending

        if self.interface == 'serial':
            self.comm_dev.write(command_text.encode('ascii'))
            if command.endswith('?') or (expect_return is True):
                return_string = ''.encode('ascii')
                while True:
                    next_char = self.comm_dev.read(1)
                    #print(ord(next_char))
                    #print(ord(self.line_ending))
                    if ord(next_char) == ord(self.line_ending):
                        break
                    return_string += next_char
                return_string = return_string.decode()

        if self.interface == 'lan':
            lan_time = time.time()
            self.comm_dev.write(command_text.encode('ascii'))
            if (command.find('?') > -1) or (expect_return is True):
                return_string = self.comm_dev.read_until(chr(10).encode('ascii'),
                                                         2).decode()
            LOGGER.info('Return string length: ' + str(len(return_string)))
            #time.sleep(0.025)
            LOGGER.info('lan_time for coomand ' + command_text.strip() +
                        ': ' + str(time.time() - lan_time))

        if self.interface == 'usbtmc':
            if command.find('?') > -1:
                return_string = self.comm_dev.ask(command_text)
            else:
                self.comm_dev.write(command_text)
                return_string = 'command_text'
        return return_string

    def read_software_version(self):
        """ Read version string from device """
        version_string = self.scpi_comm("*IDN?")
        version_string = version_string.strip()
        return version_string

    def reset_device(self):
        """ Rest device """
        self.scpi_comm("*RST")
        return True

    def device_clear(self):
        """ Stop current operation """
        self.scpi_comm("*abort")
        return True

    def clear_error_queue(self):
        """ Clear error queue """
        error = self.scpi_comm("*ESR?")
        self.scpi_comm("*cls")
        return error
