import time

class SCPI:

    def scpi_comm(self,command):
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
    
    def readSoftwareVersion(self, short=False):
        version_string = self.scpi_comm("*IDN?")
        return(version_string)    
    
    def resetDevice(self):
        self.scpi_comm("*RST")
        return(True)

    def deviceClear(self):
        self.scpi_comm("*abort")
        return(True)

    def clearErrorQueue(self):
        error = self.scpi_comm("*ESR?")
        self.scpi_comm("*cls")
        return(error)
