import time
from SCPI import SCPI


class InterfaceOutOfBoundsError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class CPX400DPDriver(SCPI):

    def __init__(self,output):
        SCPI.__init__(self,'/dev/ttyACM0','serial')
        if not (output == 1 or output == 2):
            raise InterfaceOutOfBoundsError(output)
        else:
            self.output = str(output)
        #print "SCPI Complete"

    def SetVoltage(self, value):
        """Sets the voltage """
        function_string = 'V' + self.output + ' ' + str(value)
        return(self.scpi_comm(function_string))

    def SetCurrentLimit(self, value):
        """Sets the current limit"""
        function_string = 'I ' + self.output
        return(self.scpi_comm(function_string))

    def ReadSetVoltage(self):
        """Reads the set voltage""" 
        function_string = 'V' + self.output + '?'
        return(self.scpi_comm(function_string))

    def ReadCurrentLimit(self):
        """Reads the current limit"""
        function_string = 'I' + self.output + '?'
        return(self.scpi_comm(function_string))

    def ReadActualVoltage(self):
        """Reads the actual output voltage"""
        function_string = 'V' + self.output + 'O?'
        return(self.scpi_comm(function_string))

    def ReadActualCurrent(self):
        """Reads the actual output current"""
        function_string = 'I' + self.output + 'O?'
        return(self.scpi_comm(function_string))
       
    def SetVoltageStepSize(self, value):
        """Sets the voltage step size"""
        function_string = 'DELTAV' + self.output + ' ' + str(value)
        return(self.scpi_comm(function_string))

    def SetCurrentStepSize(self, value):
        """Sets the current step size"""
        function_string = 'DELTAI' + self.output + ' ' + str(value)
        return(self.scpi_comm(function_string))

    def ReadVoltageStepSize(self):
        """Reads the voltage step size"""
        function_string = 'DELTAV' + self.output + '?'
        return(self.scpi_comm(function_string))

    def ReadCurrentStepSize(self):
        function_string = 'DELTAI' + self.output + '?'
        return(self.scpi_comm(function_string))

    def IncreaseVoltage(self):
        function_string = 'INCV' + self.output
        return(self.scpi_comm(function_string))

    def OutputStatus(self, on=False):
        if on:
            enabled = str(1)
        else:
            enabled = str(0)
        function_string = 'OP' + self.output + ' ' + enabled
        return(self.scpi_comm(function_string))

    def ReadOutputStatus(self):
        function_string = 'OP' + self.output + '?'
        return(self.scpi_comm(function_string))

    def GetLock(self):
        function_string = 'IFLOCK'
        self.scpi_comm(function_string)
        function_string = 'IFLOCK?'
        status = int(self.scpi_comm(function_string))
        return_message = ""
        if status == 0:
            return_message = "Not successful"
        if status == -1:
            return_message = "Device alreadt locked"
        if status == 1:
            return_message = "Lock acquired"
        return(return_message)

