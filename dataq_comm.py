import serial
import time

class dataq_comm():

    def __init__(self,port):
        self.f = serial.Serial(port)
	time.sleep(0.1)

    def comm(self,command):
	end_string = chr(13) #Carriage return
	self.f.write(command + end_string)
	time.sleep(0.5)
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

    def startMeasurement(self):
	command = 'start'
	self.comm(command)

    def stopMeasurement(self):
	command = 'stop'
	self.comm(command)

    def ch1Analog(self):
	command = 'slist 0 x0000'
	self.comm(command)

    def ch2Analog(self):
	command = 'slist 1 x0001'
	self.comm(command)

    def ch3Analog(self):
	command = 'slist 2 x0002'
	self.comm(command)

    def setASCIIMode(self):
	command = 'asc'
	self.comm(command)

    def setFloatMode(self):
	command = 'float'
	self.comm(command)

if __name__ == '__main__':
    dataq = dataq_comm('/dev/ttyACM0')
#    dataq.dataq()
#    dataq.deviceName()
#    dataq.firmware()
#    dataq.serialNumber()
#    dataq.setASCIIMode()
    dataq.ch1Analog()
    dataq.ch2Analog()
    dataq.ch3Analog()
    dataq.setFloatMode()
    for i in range(1,10):
        dataq.startMeasurement()
    else:
        dataq.stopMeasurement()

