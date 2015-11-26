import time
import serial
import random
import telnetlib

class MBus(object):
    """http://www.m-bus.com/mbusdoc/md5.php"""
    def __init__(self, interface, device='', tcp_port=5025, hostname=''):
        self.device = device
        self.interface = interface
        try:
            if self.interface == 'file':
                self.f = open(self.device, 'w')
                self.f.close()
            elif self.interface == 'serial':
                self.f = serial.Serial(
                    port = device,
                    baudrate = 2400,
                    parity=serial.PARITY_EVEN,
                    stopbits=serial.STOPBITS_ONE,
                    timeout = 0.5)
            elif self.interface == 'lan':
                self.f = telnetlib.Telnet(hostname, tcp_port)
            self.debug = False
        except Exception,e:
            self.debug = True
            #print "Debug mode: " + str(e)
        
    def read(self,):
        error = False
        r = self.f.read(256)
        reply = [ord(_r) for _r in r]
        toReturn = None
        if len(reply) == 0:
            # No reply
            pass
        elif reply[0] == 0xe5:
            # acknologes
            T = 'Acknologees'
            pass
        elif reply[0] == 0x10:
            # short frame
            T = 'ShortFrame'
            self.read_ShortFrame(reply)
            pass
        elif reply[0] == 0x68:
            if reply[1] == 3:
                #control frame
                T = 'ControlFrame'
                L = reply[1]
            elif reply[1] > 3: 
                #long frame
                T = 'LongFrame'
                L = reply[1]
                toReturn = self.read_LongFrame(reply)
                #print(toReturn)
            else:
                error = True
        else:
            error = True
        return toReturn
    
    def read_ShortFrame(self, reply):
        startbyte = reply[0]
        CF = reply[1]
        AF = reply[2]
        checksum = reply[3]
        endbyte = reply[4]
    
    def read_ControlFrame(self, reply):
        pass
    
    def read_LongFrame(self, reply):
        #print('read long frame')
        #print(reply)
        error = False
        startbyte = reply[0]
        if startbyte != 0x68:
            error = True
            print('error: wrong startbyte')
        L1 = reply[1]
        L2 = reply[2]
        if L1 != L2 or L1 != len(reply) - 6:
            error = True
            print('error: lenght does not match')
        if startbyte != reply[3]:
            error = True
            print('error: wrong startbyte repeat')
        CF = reply[4]
        AF = reply[5]
        CI = reply[6]
        userdata = reply[7:-2]
        #print(userdata)
        checksum = reply[-2]
        if checksum != (sum(reply[4:-2]) % 256):
            error = True
            print('error: wrong checksum')
        endbyte = reply[-1]
        if endbyte != 0x16:
            error = True
            print('error: wrong stopbyte')
        #print(error)
        if error == True:
            userdata = None
        return userdata
        
    def write_ShortFrame(self, CF, AF):
        checksum = (CF + AF) % 256
        message = (0x10, CF, AF, checksum, 0x16)
        self.f.write(message)
        
    def write_ControlFrame(self, CF, AF, CI):
        L = 3
        checksum = (CF + AF + CI) % 256
        message = (0x68, L, L, 0x68, CF, AF, CI, checksum, 0x16)
        self.f.write(message)
        
    def write_LongFrame(self, CF, AF, CI, userdata):
        L = 3 + len(userdata)
        checksum = (CF + AF + CI + sum(userdata)) % 256
        message = (0x68, L, L, 0x68, CF, AF, CI) + userdata + (checksum, 0x16)
        self.f.write(message)
        
    def write(self, CF=None, AF=None, CI = None, userdata=None):
        if CF == None or AF == None:
            error = True
        elif CI == None:
            self.write_ShortFrame(CF, AF)
        elif userdata == None or len(userdata) == 0:
            self.write_ControlFrame(CF, AF, CI)
        elif CF != None and AF != None and CI != None and userdata != None:
            self.write_LongFrame(CF, AF, CI, userdata)
        else:
            error = True
    def close(self,):
        self.f.close()

if __name__ == '__main__':
    M = MBus('serial', device='/dev/serial/by-id/usb-Silicon_Labs_Kamstrup_M-Bus_Master_MultiPort_250D_131751521-if00-port0')
    M.write_ShortFrame(CF=0x5b, AF=13)
    print(M.read())