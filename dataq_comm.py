import serial
import time

class dataq_comm():

    def __init__(self,port):
        self.f = serial.Serial(port)
	time.sleep(0.1)

    def comm(self,command):
	end_string = chr(13) #Carriage return
	self.f.write(command + end_string)
	time.sleep(0.1)
	return_string = self.f.read(self.f.inWaiting())
	print return_string
	return return_string

    def dataq(self):
	command = 'info 0'
	self.comm(command)

    def deviceName(self):
	command = 'info 1'
	self.comm(command)

    def firmware(self):
	command = 'info 2'
	self.comm(command)

    def serialNumber(self):
	command = 'info 6'
	self.comm(command)

if __name__ == '__main__':
    dataq = dataq_comm('/dev/ttyACM0')
    dataq.dataq()
    dataq.deviceName()
    dataq.firmware()
    dataq.serialNumber()
