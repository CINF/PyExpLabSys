from SCPI import SCPI

class CPX400DPDriver(SCPI):

    def __init__(self):
        SCPI.__init__(self,'/dev/ttyACM0','serial')
        
    
    def ReadSetVoltage(self, output):
        if output == 1 or output == 2:
            function_string = 'V' + str(output) + '?'
            return(self.scpi_comm(function_string))
        else:
            return False


    def ReadActualVoltage(self, output):
        if output == 1 or output == 2:
            function_string = 'V' + str(output) + 'O?'
            return(self.scpi_comm(function_string))
        else:
            return False
        

    def ReadActualCurrent(self, output):
        if output == 1 or output == 2:
            function_string = 'I' + str(output) + 'O?'
            return(self.scpi_comm(function_string))
        else:
            return False
