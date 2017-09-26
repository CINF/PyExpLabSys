# pylint: disable=R0913
""" Driver for CPX400DP power supply """
from __future__ import print_function
import time
import logging
from PyExpLabSys.drivers.scpi import SCPI
from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

class InterfaceOutOfBoundsError(Exception):
    """ Error class for CPX400DP Driver """
    def __init__(self, value):
        super(InterfaceOutOfBoundsError, self).__init__(value)
        self.value = value

    def __str__(self):
        return repr(self.value)


class CPX400DPDriver(SCPI):
    """Actual driver for the CPX400DP """

    def __init__(self, output, interface, hostname='', device='', tcp_port=0):
        self.hostname = hostname
        if interface == 'lan':
            SCPI.__init__(self, 'lan', tcp_port=tcp_port, hostname=hostname)
        if interface == 'serial':
            SCPI.__init__(self, 'serial', device=device, line_ending='\n')
        if not (output == 1 or output == 2):
            raise InterfaceOutOfBoundsError(output)
        else:
            self.output = str(output)

    def set_voltage(self, value):
        """Sets the voltage """
        function_string = 'V' + self.output + ' ' + str(value)
        return self.scpi_comm(function_string)

    def set_current_limit(self, value):
        """Sets the current limit"""
        function_string = 'I' + self.output + ' ' + str(value)
        return self.scpi_comm(function_string)

    def read_set_voltage(self):
        """Reads the set voltage"""
        function_string = 'V' + self.output + '?'
        value_string = self.scpi_comm(function_string)
        try:
            value = float(value_string.replace('V' + self.output, ''))
        except ValueError:
            value = -9997
        return value

    def read_current_limit(self):
        """Reads the current limit"""
        function_string = 'I' + self.output + '?'
        value_string = self.scpi_comm(function_string)
        try:
            value = float(value_string.replace('I' + self.output, ''))
        except ValueError:
            value = -999999
        return value

    def read_configuration_mode(self):
        """ Return the depency mode between the channels """
        configuration_mode = self.scpi_comm('CONFIG?').strip()
        mode = 'Unknown'
        if configuration_mode == '0':
            mode = 'Voltage tracking'
        if configuration_mode == '2':
            mode = 'Dual output'
        if configuration_mode in ('3', '4'):
            mode = 'Track Voltage and Current'
        return mode

    def set_dual_output(self, dual_output=True):
        """ Sets voltage tracking or dual output
        If dual_output is True, Dual output will be activated.
        If dual_output is False, Voltage tracking will be enabled """
        if dual_output:
            self.scpi_comm('CONFIG 2')
        else:
            self.scpi_comm('CONFIG 3')
        status = self.read_configuration_mode()
        return status

    def read_actual_voltage(self):
        """Reads the actual output voltage"""
        function_string = 'V' + self.output + 'O?'
        value_string = self.scpi_comm(function_string)
        LOGGER.warn(value_string)
        time.sleep(0.1) # This might only be necessary on LAN interface
        try:
            value = float(value_string.replace('V', ''))
        except ValueError:
            value = -999999
        return value

    def read_actual_current(self):
        """Reads the actual output current"""
        function_string = 'I' + self.output + 'O?'
        value_string = self.scpi_comm(function_string)
        time.sleep(0.1) # This might only be necessary on LAN interface
        try:
            value = float(value_string.replace('A', ''))
        except ValueError:
            value = -9998
        return value

    def set_voltage_stepsize(self, value):
        """Sets the voltage step size"""
        function_string = 'DELTAV' + self.output + ' ' + str(value)
        return self.scpi_comm(function_string)

    def set_current_stepsize(self, value):
        """Sets the current step size"""
        function_string = 'DELTAI' + self.output + ' ' + str(value)
        return self.scpi_comm(function_string)

    def read_voltage_stepsize(self):
        """Reads the voltage step size"""
        function_string = 'DELTAV' + self.output + '?'
        return self.scpi_comm(function_string)

    def read_current_stepsize(self):
        """ Read the current stepszie """
        function_string = 'DELTAI' + self.output + '?'
        return self.scpi_comm(function_string)

    def increase_voltage(self):
        """ Increase voltage one step """
        function_string = 'INCV' + self.output
        return self.scpi_comm(function_string)

    def output_status(self, output_on=False):
        """ Set the output status """
        if output_on:
            enabled = str(1)
        else:
            enabled = str(0)
        function_string = 'OP' + self.output + ' ' + enabled
        return self.scpi_comm(function_string)

    def read_output_status(self):
        """ Read the output status """
        function_string = 'OP' + self.output + '?'
        return self.scpi_comm(function_string)

    def get_lock(self):
        """ Lock the instrument for remote operation """
        function_string = 'IFLOCK'
        self.scpi_comm(function_string)
        function_string = 'IFLOCK?'
        status = int(self.scpi_comm(function_string))
        return_message = ""
        if status == 0:
            return_message = "Not successful"
        if status == -1:
            return_message = "Device already locked"
        if status == 1:
            return_message = "Lock acquired"
        return return_message

if __name__ == '__main__':
    CPX = CPX400DPDriver(1, interface='serial', device='/dev/ttyACM0')
    print(CPX.read_software_version())
    print(CPX.read_current_limit())
    print(CPX.read_actual_current())
    print(CPX.read_configuration_mode())
    print(CPX.set_dual_output(False))
