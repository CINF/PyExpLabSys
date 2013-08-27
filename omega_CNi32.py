import serial
import time
import FindSerialPorts

class omega_comm():

    def __init__(self,port):
        self.f = serial.Serial(port,9600,bytesize=serial.SEVENBITS,parity=serial.PARITY_ODD,timeout=1)
	time.sleep(0.1)

    def comm(self,command):
        pre_string = chr(42)
	end_string = chr(13)
        length_command = len(command)
	self.f.write(pre_string + command + end_string)
	time.sleep(0.5)
	return_string = self.f.read(self.f.inWaiting())

        #Remove the echo response from the device
	return_string = return_string[length_command:]
	
	return return_string
		
    def ResetDevice(self):
        command = 'Z02'
	return_string = self.comm(command)
	return return_string
		
    def ReadTemperature(self):
        command = 'X01'
	signal = self.comm(command)
        val = -9999
        while val < -9998: #This error handling must be improved...
            try:
                val = float(signal)
            except ValueError:
                val = -9997
	return(val)


if __name__ == '__main__':
    ports = FindSerialPorts.find_ports()
    for p in ports:
        print p
        omega = omega_comm('/dev/' + p)
        if omega.ReadTemperature() > -9000:
            print omega.ReadTemperature()
            break

    print omega.ReadTemperature()
