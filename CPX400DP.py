from SCPI import SCPI

class InterfaceOutOfBoundsError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class CPX400DPDriver(SCPI):

    def __init__(self):
        SCPI.__init__(self,'/dev/ttyACM0','serial')
    
    def ReadSetVoltage(self, output):
        if not (output == 1 or output == 2):
            raise InterfaceOutOfBoundsError(output)
        function_string = 'V' + str(output) + '?'

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
