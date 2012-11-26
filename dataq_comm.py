import serial
import time

class dataq_comm():

    

    def __init__(self,port):
        self.f = serial.Serial(port)
	time.sleep(0.1)
        self.slist_counter = 0
	
#There is no check on slist_counter and it can hence be overflowed!

    def comm(self,command):
	end_string = chr(13) # carriage return
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
	command = 'slist ' + str(self.slist_counter) + ' x0000'
	self.slist_counter = self.slist_counter + 1
	print command, self.slist_counter
	self.comm(command)

    def ch2Analog(self):
	command = 'slist ' + str(self.slist_counter) + ' x0001'
	self.slist_counter = self.slist_counter + 1
	self.comm(command)

    def ch3Analog(self):
	global slist_counter
	command = 'slist ' + str(self.slist_counter) + ' x0002'
	self.slist_counter = self.slist_counter + 1
	self.comm(command)

    def setASCIIMode(self):
	command = 'asc'
	self.comm(command)

    def setFloatMode(self):
	command = 'float'
	self.comm(command)

    def resetSlist(self):
	global slist_counter
	for i in range(0,5):
	    command = 'slist ' + str(i) + ' 0xffff'
	    self.comm(command)
	else:
            slist_counter = 0

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

