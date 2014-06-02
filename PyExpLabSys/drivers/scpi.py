import time
import serial
import random
import telnetlib

class SCPI:

    def __init__(self,device,port):
        self.device = device
        self.port = port
        try:
            if self.port == 'file':
                self.f = open(self.device, 'w')
                self.f.close()
            if self.port == 'serial':
                self.f = serial.Serial(self.device, 9600, timeout=1,xonxoff=True)
            if self.port == 'lan':
                #self.f = telnetlib.Telnet('agilent-34972a',5025)
                self.f = telnetlib.Telnet(device,5025)
            self.debug = False
        except Exception,e:
            self.debug = True
            #print "Debug mode: " + str(e)

    def scpi_comm(self, command, expect_return=False):
        #print self.f.xonxoff
        return_string = ""
        if self.debug:
            return str(random.random())
        if self.port == 'file':
            self.f = open(self.device, 'w')
            self.f.write(command)
            time.sleep(0.02)
            self.f.close()
            time.sleep(0.1)
            if command.find('?') > -1:
                self.f = open(self.device, 'r')
                return_string = self.f.readline()
                self.f.close()
        if self.port == 'serial':
            self.f.write(command + '\n')
            if command.endswith('?') or (expect_return is True):
                return_string = self.f.readline()
        if self.port == 'lan':
            self.f.write(command + '\n')
            if command.find('?') > -1:
                return_string = self.f.read_until(chr(10),2)
        return return_string
    
    def read_software_version(self, short=False):
        version_string = self.scpi_comm("*IDN?")
        return(version_string)    
    
    def reset_device(self):
        self.scpi_comm("*RST")
        return(True)

    def device_clear(self):
        self.scpi_comm("*abort")
        return(True)

    def clear_error_queue(self):
        error = self.scpi_comm("*ESR?")
        self.scpi_comm("*cls")
        return(error)
