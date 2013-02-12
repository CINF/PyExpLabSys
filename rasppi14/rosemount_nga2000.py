import serial
import time

class AK_comm():

    def __init__(self,port):
        self.f = serial.Serial(port,9600,xonxoff=True,timeout=2)
	time.sleep(0.1)

    def comm(self,command):
        pre_string = chr(2) + chr(32)
	end_string = chr(3)
	self.f.write(pre_string + command + end_string)
	time.sleep(0.2)
	return_string = self.f.read(self.f.inWaiting())

        #The first two and the last character is not part of the message
        #print ord(return_string[-1]) #Check that last character is chr(3)
	return_string = return_string[2:]
	return_string = return_string[:-1]
	error_byte = return_string[5] #Check error byte!
	return_string = return_string[7:] #The first part of the message is an echo of the command
	
	return return_string
		
    def IdentifyDevice(self):
        command = 'AGID K0'
	id = self.comm(command)
	return_string = ''
	dev_id = id.split('/')
	return_string += "Name and s/n: " + dev_id[0] + "\n"
	return_string += "Program version: " + dev_id[1] + "\n"
	return_string += "Data: " + dev_id[2] + "\n"
	return return_string
		
    def ReadConcentration(self):
        command = 'AKON K1'
	signal = self.comm(command)
        print "Signal: " + signal
        if signal[0] == "#":
            signal = signal[1:]
	return(float(signal))

    def ReadTemperature(self):
        command = 'ATEM K1'
	signal = self.comm(command)
	return(float(signal)-273.15)

    def ReadUncorrelatedAnalogValue(self):
        command = 'AUKA K1'
	signal = self.comm(command)
	range = int(signal[1])
	sensor_output = signal[3:]
        sensor_number = float(sensor_output)
        sensor_number = int(sensor_number)
	return(sensor_number)

    def ReadOperationalHours(self):
        command = 'ABST K1'
	signal = self.comm(command)
	return(signal)


if __name__ == '__main__':
    AK = AK_comm('/dev/ttyUSB0')
    #print AK.IdentifyDevice()
    print "Concentration: " + str(AK.ReadConcentration())
    print "Temperature: " + str(AK.ReadTemperature())
    print "Raw signal: " + str(AK.ReadUncorrelatedAnalogValue())
    print "Operational hours " + str(AK.ReadOperationalHours())

    #f = serial.Serial('com1',9600,xonxoff=True)
    #time.sleep(0.1)
    #f.write(chr(2) + chr(32) + 'AGID K0' + chr(3))
    #time.sleep(0.2)
    #print f.inWaiting()
    #print f.read(f.inWaiting())
