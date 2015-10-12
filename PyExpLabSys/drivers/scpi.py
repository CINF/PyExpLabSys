import time
import serial
import random
import telnetlib

class SCPI:

    def __init__(self, interface, device='', tcp_port=5025, hostname=''):
        self.device = device
        self.interface = interface
        try:
            if self.interface == 'file':
                self.f = open(self.device, 'w')
                self.f.close()
            if self.interface == 'serial':
                self.f = serial.Serial(self.device, 9600, timeout=1, xonxoff=True)
            if self.interface == 'lan':
                self.f = telnetlib.Telnet(hostname, tcp_port)
            self.debug = False
        except Exception,e:
            self.debug = True
            #print "Debug mode: " + str(e)

    def scpi_comm(self, command, expect_return=False):
        #print self.f.xonxoff
        return_string = ""
        if self.debug:
            return str(random.random())
        if self.interface == 'file':
            self.f = open(self.device, 'w')
            self.f.write(command)
            time.sleep(0.02)
            self.f.close()
            time.sleep(0.05)
            if command.find('?') > -1:
                self.f = open(self.device, 'r')
                return_string = self.f.readline()
                self.f.close()
        if self.interface == 'serial':
            self.f.write(command + '\n')
            if command.endswith('?') or (expect_return is True):
                return_string = self.f.readline()
        if self.interface == 'lan':
            self.f.write(command + '\n')
            if (command.find('?') > -1) or (expect_return is True):
                return_string = self.f.read_until(chr(10),2)
        return return_string
    
    def read_software_version(self, short=False):
        version_string = self.scpi_comm("*IDN?")
        version_string = version_string.strip()
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
