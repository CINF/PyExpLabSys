import serial
import time

class omega_comm():

    def __init__(self,port,comm_stnd='rs232'):
        self.f = serial.Serial(port,9600,bytesize=serial.SEVENBITS,parity=serial.PARITY_ODD,timeout=2)
        self.comm_stnd = comm_stnd
	time.sleep(0.1)

    def comm(self,command, address=1):
        pre_string = chr(42)
	end_string = chr(13)
        if self.comm_stnd == 'rs485':
            length_command = len(command) + 2
        else:
            length_command = len(command)
        if self.comm_stnd == 'rs485':
            comm_string = pre_string + '0' + str(address) + command + end_string
        else:
            comm_string = pre_string + command + end_string
        self.f.write(comm_string)

	time.sleep(0.5)
	return_string = self.f.read(self.f.inWaiting())

        #Remove the echo response from the device
	return_string = return_string[length_command:]
	
	return return_string

    def SetCType(self, address):
        command = 'W0724'
	return_string = self.comm(command)
	return return_string       

    def SetKType(self, address):
        command = 'W0704'
	return_string = self.comm(command)
	return return_string       
		
    def ResetDevice(self):
        command = 'Z02'
	return_string = self.comm(command)
	return return_string
		
    def ReadTemperature(self, address=1):
        command = 'X01'
	signal = self.comm(command, address)
        val = -9999
        while val < -9998:
            try:
                val = float(signal)
            except ValueError:
                val = -9999
	return(val)


if __name__ == '__main__':
    omega = omega_comm('/dev/ttyUSB0', comm_stnd='rs485')
    print 'Setting device 1 to C-type'
    print omega.SetCType(1)
    print '----'
    print "Temperature: " + str(omega.ReadTemperature(address=1))
    print "Temperature: " + str(omega.ReadTemperature(address=2))

