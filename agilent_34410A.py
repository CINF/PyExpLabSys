import time

class Agilent34410ADriver:

    def scpi_comm(self,command):
        #ser = serial.Serial(0)
        #comm = "#00" + command + "\r"

        f = open('/dev/usbtmc0', 'w')
        f.write(command)
        f.close()

        time.sleep(0.01)
        return_string = ""    
        if command[-1]=='?':
            a = ' '
            f = open('/dev/usbtmc0', 'r')
            while not (ord(a) == 10):
                a = f.read(1)
                return_string += a
            f.close()
        return return_string
        
    def readSoftwareVersion(self):
        version_string = scpi_comm("*IDN?")
        return(version_string)

    def resetDevice(self):
        scpi_comm("*RST")
        return(True)

    def deviceClear(self):
        scpi_comm("*abort")
        return(True)

    def clearErrorQueue(self):
        error = scpi_comm("*ESR?")
        scpi_comm("*cls")
        return(error)


    def configCurrentMeasurement(self):
        scpi_comm("CONFIGURE:CURRENT:DC") #Take parameter to also be able to select AC
        return(True)

    def configResistanceMeasurement(self):
        scpi_comm("CONFIGURE:RESISTANCE") #Take parameter to also be able to select 4W
        return(True)

    def selectMeasurementFunction(self,function):
        values = ['CAPACITANCE','CONTINUITY','CURRENT','DIODE','FREQUENCY','RESISTANCE','TEMPERATURE','VOLTAGE']

    def readConfiguration(self):
        response = scpi_comm("CONFIGURE?")
        response = response.replace(' ',',')
        conf = response.split(',')
        conf_string = "Measurement type: " + conf[0] + "\nRange: " + conf[1] + "\nResolution: " + conf[2]
        return(conf_string)


    def read(self):
        value = self.scpi_comm("READ?")
        return value


driver  = Agilent34410ADriver()
print driver.read()
