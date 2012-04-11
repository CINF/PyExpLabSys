import time
import serial
import random

class SCPI:

    def __init__(self,device,port):
        self.device = device
        self.port = port
        try:
            if self.port == 'file':
                f = open(self.device, 'w')
            if self.port == 'serial':
                f = serial.Serial(self.device, 9600, timeout=1,xonxoff=True)
            f.close()
            self.debug = False
        except:
            self.debug = True


    def scpi_comm(self,command):
        if self.debug:
            return str(random.random())
        if self.port == 'file':
            f = open(self.device, 'w')
        if self.port == 'serial':
            f = serial.Serial(self.device, 9600, timeout=1,xonxoff=True)
            command = command + '\n'    
        f.write(command)
        f.close()

        time.sleep(0.01)
        return_string = ""    
        if command.endswith('?') or command.endswith('?\n'):
            a = ' '
            if self.port == 'file':
                f = open(self.device, 'r')
            if self.port == 'serial':
                f = serial.Serial(self.device, 9600, timeout=1)
            while not (ord(a) == 10):
                a = f.read(1)
                return_string += a
        f.close()
        return return_string
    
    def ReadSoftwareVersion(self, short=False):
        version_string = self.scpi_comm("*IDN?")
        return(version_string)    
    
    def ResetDevice(self):
        self.scpi_comm("*RST")
        return(True)

    def DeviceClear(self):
        self.scpi_comm("*abort")
        return(True)

    def ClearErrorQueue(self):
        error = self.scpi_comm("*ESR?")
        self.scpi_comm("*cls")
        return(error)
