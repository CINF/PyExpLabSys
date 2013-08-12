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

    for i in range(0,10):
        try:
            print 'ttyUSB: ' + str(i)
            omega = omega_comm('/dev/ttyUSB' + str(i))
            print str(omega.IdentifyDevice().strip())
            print "Temperature: " + str(omega.ReadTemperature())
        except:
            pass

"""
    # High pressure cell (ID: 01)
    print 'ttyUSB1: '
    omega = omega_comm('/dev/ttyUSB1')
    print str(omega.IdentifyDevice().strip())
    print "Temperature: " + str(omega.ReadTemperature())
    print ''

    # High pressure cell (ID: 01)
    #print 'ttyUSB3: '
    #omega = omega_comm('/dev/ttyUSB3')
    #print str(omega.IdentifyDevice().strip())
    #print "Temperature: " + str(omega.ReadTemperature())

    # OldClusterSource (ID: 02)
    print 'ttyUSB2: '
    omega = omega_comm('/dev/ttyUSB2')
    print str(omega.IdentifyDevice().strip())
    print "Temperature: " + str(omega.ReadTemperature())
    print ''

    # OldClusterSource (ID: 02)
    print 'ttyUSB3: '
    omega = omega_comm('/dev/ttyUSB3')
    print str(omega.IdentifyDevice().strip())
    print "Temperature: " + str(omega.ReadTemperature())

    print 'ttyUSB4: '
    omega = omega_comm('/dev/ttyUSB3')
    print str(omega.IdentifyDevice().strip())
    print "Temperature: " + str(omega.ReadTemperature())
"""
