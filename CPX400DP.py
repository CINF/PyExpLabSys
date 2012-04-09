from SCPI import SCPI

class InterfaceOutOfBoundsError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class CPX400DPDriver(SCPI):

    def __init__(self):
        SCPI.__init__(self,'/dev/ttyACM0','serial')

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

    def SetVoltage(self, output,value):
        if not (output == 1 or output == 2):
            raise InterfaceOutOfBoundsError(output)
        function_string = 'V' + str(output)
        return(self.scpi_comm(function_string))

    def SetCurrentLimit(self, output,value):
        if not (output == 1 or output == 2):
            raise InterfaceOutOfBoundsError(output)
        function_string = 'I' + str(output)
        return(self.scpi_comm(function_string))
    
    def ReadSetVoltage(self, output):
        if not (output == 1 or output == 2):
            raise InterfaceOutOfBoundsError(output)
        function_string = 'V' + str(output) + '?'
        return(self.scpi_comm(function_string))

    def ReadCurrentLimit(self, output):
        if not (output == 1 or output == 2):
            raise InterfaceOutOfBoundsError(output)
        function_string = 'I' + str(output) + '?'
        return(self.scpi_comm(function_string))


    def ReadActualVoltage(self, output):
        if not (output == 1 or output == 2):
            raise InterfaceOutOfBoundsError(output)
        function_string = 'V' + str(output) + 'O?'
        return(self.scpi_comm(function_string))

    def ReadActualCurrent(self, output):
        if not (output == 1 or output == 2):
            raise InterfaceOutOfBoundsError(output)
        function_string = 'I' + str(output) + 'O?'
        return(self.scpi_comm(function_string))
