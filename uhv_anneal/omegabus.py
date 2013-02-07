import serial
import time

class OmegaBus():

    def __init__(self):
        self.f = serial.Serial('/dev/ttyS0',9600)
        time.sleep(0.1)

    def ReadValue(self,channel):
        self.f.write("$" + str(channel) + "RD" + "\r")
        time.sleep(0.1)
        temp_string = self.f.read(self.f.inWaiting())
        if temp_string[1] == "*":
            temp_string = temp_string[3:]
        temp_fahrenheit = float(temp_string)
        temp_celsius = 5*(temp_fahrenheit-32)/9
        return float(temp_celsius)

    def ReadMax(self,channel):
        self.f.write("$" + str(channel) + "RMX" + "\r")
        time.sleep(0.25)
        temp_string = self.f.read(self.f.inWaiting())
        if temp_string[1] == "*":
            temp_string = temp_string[3:]
        return float(temp_string)

    def ReadMin(self,channel):
        self.f.write("$" + str(channel) + "RMN" + "\r")
        time.sleep(0.25)
        temp_string = self.f.read(self.f.inWaiting())
        if temp_string[1] == "*":
            temp_string = temp_string[2:]
        return float(temp_string)

    def ReadSetup(self):
        self.f.write("$" + "1RS" + "\r")
        time.sleep(0.25)
        rs_string = self.f.read(self.f.inWaiting())
        if rs_string[1] == "*":
            rs_string = rs_string[2:]
        print rs_string
        byte1 = rs_string[0:2]
        byte2 = rs_string[2:4]
        byte3 = rs_string[4:6]
        byte4 = rs_string[6:8]

        setupstring = ""
        setupstring += "Base adress: " + chr(int(byte1,16)) + "\n"

        bits_2 = (bin(int(byte2,16))[2:]).zfill(8)
        setupstring += "No linefeed\n" if bits_2[0] == '0' else "Linefeed\n"
        if bits_2[2] == '0': #bits_2[1] will contain the parity if not none
            setupstring += "Parity: None"  + "\n"
        setupstring += "Normal addressing\n" if bits_2[3] == '0' else "Extended addressing\n"
        if bits_2[4:8] == '0010':
            setupstring += "Baud rate: 9600"  + "\n"

        bits_3 = (bin(int(byte3,16))[2:]).zfill(8)
        print bits_3
        print bits_3[0]

        setupstring += "Channel 3 enabled\n" if bits_3[0] == '1' else "Channel 3 disabled\n"
        setupstring += "Channel 2 enabled\n" if bits_3[1] == '1' else "Channel 2 disabled\n"
        setupstring += "Channel 1 enabled\n" if bits_3[2] == '1' else "Channel 1 disabled\n"
        setupstring += "No cold junction compensation\n" if bits_3[3] == '1' else "Cold junction compensation enabled\n"
        setupstring += "Unit: Fahrenheit\n" if bits_3[4] == '1' else "Unit: Celsius\n"

        #print (bin(int(byte4,16))[2:]).zfill(8)
        
        return setupstring

    def ChangeTemperatureScale(self,scale):
        if not (scale=='f' or scale=='c'):
            return(False)

if __name__ == "__main__":
    omega = OmegaBus()
    print omega.ReadValue(1)
    print omega.ReadValue(2)
    print omega.ReadValue(3)
    #print omega.ReadMin(1)
    #print omega.ReadMax(1)

    print omega.ReadSetup()

    #print ChangeTemperatureScale('f')
