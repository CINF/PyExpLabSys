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
        try:
            return_string = return_string[2:]
            return_string = return_string[:-1]
            error_byte = return_string[5] #Check error byte!
            return_string = return_string[7:] #The first part of the message is an echo of the command
        except IndexError:
            return_string = "Serial Error"
            #Here we should properly raise a home-made error
        return return_string
                
    def IdentifyDevice(self):
        command = 'AGID K0'
        id = self.comm(command)
        return_string = ''
        try: 
            dev_id = id.split('/')
            return_string += "Name and s/n: " + dev_id[0] + "\n"
            return_string += "Program version: " + dev_id[1] + "\n"
            return_string += "Data: " + dev_id[2] + "\n"
        except:
            return_string = 'Error'
        return return_string
                
    def ReadConcentration(self):
        command = 'AKON K1'
        signal = self.comm(command)
        #print "Signal: " + signal
        if signal[0] == "#":
            signal = signal[1:]
        signal = signal.strip()
        signal = signal.strip(chr(3))
        return(float(signal))

    def ReadTemperature(self):
        command = 'ATEM K1'
        signal = self.comm(command)
        return(float(signal)-273.15)

    def ReadUncorrelatedAnalogValue(self):
        command = 'AUKA K1'
        signal = self.comm(command)
        #print "Signal: " + signal
        #range = int(signal[1])
        sensor_output = signal[3:]
        #for i in range(0, len(sensor_output)):
        #    print ord(sensor_output[i])
        sensor_output = sensor_output.strip()
        sensor_output = sensor_output.strip(chr(3))

        #print "Sensor output: " + sensor_output
        return(int(float(sensor_output)))

    def ReadOperationalHours(self):
        command = 'ABST K1'
        signal = self.comm(command)
        return(signal)


if __name__ == '__main__':
    AK = AK_comm('/dev/ttyUSB0')

    print("Concentration: " + str(AK.ReadConcentration()))
    print("Temperature: " + str(AK.ReadTemperature()))
    print("Raw signal: " + str(AK.ReadUncorrelatedAnalogValue()))
    print("Operational hours " + str(AK.ReadOperationalHours()))
