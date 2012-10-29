from SCPI import SCPI

    
class Agilent34410ADriver(SCPI):

    def __init__(self):
        SCPI.__init__(self,'/dev/usbtmc0','file')

    def configCurrentMeasurement(self):
        self.scpi_comm("CONFIGURE:CURRENT:DC") #Take parameter to also be able to select AC
        return(True)

    def configResistanceMeasurement(self):
        self.scpi_comm("CONFIGURE:RESISTANCE") #Take parameter to also be able to select 4W
        return(True)

    def SelectMeasurementFunction(self,function):
        values = ['CAPACITANCE','CONTINUITY','CURRENT','DIODE','FREQUENCY','RESISTANCE','FRESISTANCE','TEMPERATURE','VOLTAGE']
        return_value = False
        if function in values:
            return_value = True
            function_string = "FUNCTION " + "\"" + function + "\""
            self.scpi_comm(function_string)
            
        return(return_value)

    def readConfiguration(self):
        response = self.scpi_comm("CONFIGURE?")
        response = response.replace(' ',',')
        conf = response.split(',')
        conf_string = "Measurement type: " + conf[0] + "\nRange: " + conf[1] + "\nResolution: " + conf[2]
        return(conf_string)

    def setAutoInputZ(self, auto=False):
        if auto:
            self.scpi_comm("VOLT:IMP:AUTO ON")
        else:
            self.scpi_comm("VOLT:IMP:AUTO OFF")

    def Read(self):
        value = float(self.scpi_comm("READ?"))
        return value


