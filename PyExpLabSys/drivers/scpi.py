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
try:
    import Gpib
except ImportError:
    Gpib = None

LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
LOGGER.addHandler(logging.NullHandler())


class SCPI(object):
    """ Driver for scpi communication """
    def __init__(self, interface, device='', tcp_port=5025, hostname='',
                 baudrate=9600, visa_string='', gpib_address=None, line_ending='\r',
                 encoding='ascii'):
        self.device = device
        self.line_ending = line_ending
        self.interface = interface
        self.encoding = encoding
        if self.interface == 'file':
            self.comm_dev = open(self.device, 'w')
            self.comm_dev.close()
        if self.interface == 'serial':
            self.comm_dev = serial.Serial(self.device, baudrate,
                                          timeout=3, xonxoff=True)
        if self.interface == 'lan':
            self.comm_dev = telnetlib.Telnet(hostname, tcp_port)
        if self.interface == 'usbtmc':
            if usbtmc is None:
                exit('usbtmc is not availalbe')
            self.comm_dev = usbtmc.Instrument(visa_string)
        if self.interface == 'gpib':
            if Gpib is None:
                exit('gpib is not availalbe')
            self.comm_dev = Gpib.Gpib(0, pad=gpib_address)

    def scpi_comm(self, command, expect_return=False):
        """ Implements actual communication with SCPI instrument """
        return_string = ""
        if self.interface == 'file':
            self.comm_dev = open(self.device, 'wb')
            self.comm_dev.write(bytes(command + self.line_ending, self.encoding))
            self.comm_dev.flush()
            self.comm_dev.close()
            if ('?' in command) or (expect_return is True):
                self.comm_dev = open(self.device, 'rb')
                time.sleep(0.002)
                t = time.time()
                while len(return_string) == 0:
                    dt = time.time() - t
                    if dt > 1:
                        raise ValueError
                    return_string = self.comm_dev.read(1)
                return_string += self.comm_dev.readline()
                return_string = return_string.decode(self.encoding)
                self.comm_dev.close()

        command_text = command + self.line_ending
        if self.interface == 'serial':
            self.comm_dev.write(command_text.encode('ascii'))
            if command.endswith('?') or (expect_return is True):
                return_string = ''.encode(self.encoding)
                while True:
                    next_char = self.comm_dev.read(1)
                    # print(next_char)
                    if ord(next_char) == ord(self.line_ending):
                        break
                    return_string += next_char
                return_string = return_string.decode(self.encoding)

        if self.interface == 'lan':
            lan_time = time.time()
            command_text = command + '\n'
            # print('Command text ', repr(command_text))
            self.comm_dev.write(command_text.encode(self.encoding))
            if command.endswith('?') or (expect_return is True):
                raw = self.comm_dev.expect([b'\n'], 2)
                return_string = raw[2].decode().strip()

                # ENT? return an extra newlinw from the inline reply
                if command_text.find('ENT?'):
                    # extra_n = self.comm_dev.read_until(b'\n', 0.1).decode()
                    self.comm_dev.read_until(b'\n', 0.1).decode()

            LOGGER.info('Return string length: ' + str(len(return_string)))
            LOGGER.info('lan_time for command ' + command_text.strip() +
                        ': ' + str(time.time() - lan_time))
            LOGGER.info('Return string length: ' + str(len(return_string)))
            LOGGER.info('lan_time for command ' + command_text.strip() +
                        ': ' + str(time.time() - lan_time))

        if self.interface == 'usbtmc':
            if command.find('?') > -1:
                return_string = self.comm_dev.ask(command_text)
            else:
                self.comm_dev.write(command_text)
                return_string = 'command_text'

        if self.interface == 'gpib':
            self.comm_dev.write(command_text)
            if command.endswith('?') or expect_return:
                return_string = self.comm_dev.read().strip().decode()
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
