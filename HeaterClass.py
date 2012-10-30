import CPX400DP as CPX
import time

class CPXHeater():

    def __init__(self,number_of_outputs):
        """ We assume that number_of_outputs is either 1 or 2"""
        self.N = number_of_outputs
        self.CPX1  = CPX.CPX400DPDriver(1)
        if self.N == 2:
            time.sleep(0.1)
            self.CPX2  = CPX.CPX400DPDriver(2)

    def SetVoltage(self, value):
        """Sets the voltage """
        self.CPX1.SetVoltage(value)
        if self.N == 2:
            self.CPX2.SetVoltage(value)
        return(None)

    def SetCurrentLimit(self, value):
        return(none)

    def ReadSetVoltage(self):
        return(None)

    def ReadCurrentLimit(self):
        return(None)

    def ReadActualVoltage(self):
        return(None)

    def ReadActualCurrent(self):
        I1 = self.CPX1.ReadActualCurrent()
        if self.N == 2:
            time.sleep(0.1)
            I2 = self.CPX2.ReadActualCurrent()
        else:
            I2 = 0
        return(I1,I2)
       
    def SetVoltageStepSize(self, value):
        return(None)

    def SetCurrentStepSize(self, value):
        return(None)

    def ReadVoltageStepSize(self):
        return(None)

    def ReadCurrentStepSize(self):
        return(None)

    def IncreaseVoltage(self):
        return(None)

    def OutputStatus(self, on=False):
        self.CPX1.OutputStatus(on)
        if self.N == 2:
            self.CPX2.OutputStatus(on)
        return(None)

    def ReadOutputStatus(self):
        return(None)

    def GetLock(self):
        return(None)
