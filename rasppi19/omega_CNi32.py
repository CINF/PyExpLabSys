import serial
import time

class omega_comm():

    def __init__(self,port):
        self.f = serial.Serial(port,9600,bytesize=serial.SEVENBITS,parity=serial.PARITY_ODD,timeout=2)
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

    def IdentifyDevice(self):
        command = 'R26'
        return_string = self.comm(command)
        return return_string

    def NameDevice(self, char):
        command = 'W26' + char
        return_string = self.comm(command)
        return return_string
		
    def ReadTemperature(self):
        command = 'X01'
        signal = self.comm(command)
        try:
            val = float(signal)
        except ValueError:
            val = -9999
        return(val)


if __name__ == '__main__':
    #STM (ID: 02)
    omega = omega_comm('/dev/ttyUSB0')
    print "Temperature: " + str(omega.ReadTemperature())

    # High pressure cell (ID: 01)
    omega = omega_comm('/dev/ttyUSB2')
    print "Temperature: " + str(omega.ReadTemperature())

