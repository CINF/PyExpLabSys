import time
from scpi import SCPI


class InterfaceOutOfBoundsError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class CPX400DPDriver(SCPI):

    def __init__(self,output, port):
        SCPI.__init__(self, port, 'serial')
        if not (output == 1 or output == 2):
            raise InterfaceOutOfBoundsError(output)
        else:
            self.output = str(output)
        #print "SCPI Complete"

    def set_voltage(self, value):
        """Sets the voltage """
        function_string = 'V' + self.output + ' ' + str(value)
        return(self.scpi_comm(function_string))

    def set_current_limit(self, value):
        """Sets the current limit"""
        function_string = 'I' + self.output + ' ' + str(value)
        return(self.scpi_comm(function_string))

    def read_set_voltage(self):
        """Reads the set voltage"""
        function_string = 'V' + self.output + '?'
        return(self.scpi_comm(function_string))

    def read_current_limit(self):
        """Reads the current limit"""
        function_string = 'I' + self.output + '?'
        return(self.scpi_comm(function_string))

    def read_actual_voltage(self):
        """Reads the actual output voltage"""
        function_string = 'V' + self.output + 'O?'
        value_string = self.scpi_comm(function_string)
        try:
            value = float(value_string.replace('V', ''))
        except ValueError:
            value = -999999
        return(value)

    def read_actual_current(self):
        """Reads the actual output current"""
        function_string = 'I' + self.output + 'O?'
        value_string = self.scpi_comm(function_string)
        try:
            value = float(value_string.replace('A', ''))
        except ValueError:
            value = -9998
        return(value)

    def set_voltage_stepsize(self, value):
        """Sets the voltage step size"""
        function_string = 'DELTAV' + self.output + ' ' + str(value)
        return(self.scpi_comm(function_string))

    def set_current_stepsize(self, value):
        """Sets the current step size"""
        function_string = 'DELTAI' + self.output + ' ' + str(value)
        return(self.scpi_comm(function_string))

    def read_voltage_stepsize(self):
        """Reads the voltage step size"""
        function_string = 'DELTAV' + self.output + '?'
        return(self.scpi_comm(function_string))

    def read_current_stepsize(self):
        """ Read the current stepszie """
        function_string = 'DELTAI' + self.output + '?'
        return(self.scpi_comm(function_string))

    def increase_voltage(self):
        """ Increase voltage one step """
        function_string = 'INCV' + self.output
        return(self.scpi_comm(function_string))

    def output_status(self, on=False):
        """ Set the output status """
        if on:
            enabled = str(1)
        else:
            enabled = str(0)
        function_string = 'OP' + self.output + ' ' + enabled
        return(self.scpi_comm(function_string))

    def read_output_status(self):
        """ Read the output status """
        function_string = 'OP' + self.output + '?'
        return(self.scpi_comm(function_string))

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
        return(return_message)


if __name__ == '__main__':
    cpx = CPX400DPDriver(1)
    print cpx.read_current_limit()

    cpx = CPX400DPDriver(2)
    print cpx.read_current_limit()
