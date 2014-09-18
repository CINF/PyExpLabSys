import serial
import time

class OmegaBus():

    def __init__(self,port):
        self.f = serial.Serial(port,9600)
        time.sleep(1.0)

    def ReadValue(self,channel):
        self.f.write("$" + str(channel) + "RD" + "\r")
        time.sleep(1)
        temp_string = self.f.read(self.f.inWaiting())
        #print temp_string
        #self.f.close()
        if temp_string[1] == "*":
            temp_string = temp_string[3:]
        #temp_celsius = float(temp_string)
        temp_fahrenheit = float(temp_string)
        temp_celsius = 5*(temp_fahrenheit-32)/9
        return float(temp_celsius)

    def ReadMax(self,channel):
        self.f.write("$" + str(channel) + "RMX" + "\r")
        time.sleep(1)
        temp_string = self.f.read(self.f.inWaiting())
        if temp_string[1] == "*":
            temp_string = temp_string[3:]
        return float(temp_string)

    def ReadMin(self,channel):
        self.f.write("$" + str(channel) + "RMN" + "\r")
        time.sleep(1)
        temp_string = self.f.read(self.f.inWaiting())
        if temp_string[1] == "*":
            temp_string = temp_string[2:]
        return float(temp_string)

    def ReadSetup(self):
        self.f.write("$" + "1RS" + "\r")
        time.sleep(1)
        rs_string = self.f.read(self.f.inWaiting())
        if rs_string[1] == "*":
            rs_string = rs_string[2:]
        byte1 = rs_string[0:2]
        byte2 = rs_string[2:4]
        byte3 = rs_string[4:6]
        byte4 = rs_string[6:8]
        setupstring = ""
        setupstring += 'Raw respond: ' + str(rs_string) + '\n'
        setupstring += "Base adress: " + chr(int(byte1,16)) + "\n"

        bits_2 = (bin(int(byte2,16))[2:]).zfill(8)
        setupstring += "No linefeed\n" if bits_2[0] == '0' else "Linefeed\n"
        if bits_2[2] == '0': #bits_2[1] will contain the parity if not none
            setupstring += "Parity: None"  + "\n"
        setupstring += "Normal addressing\n" if bits_2[3] == '0' else "Extended addressing\n"
        if bits_2[4:8] == '0010':
            setupstring += "Baud rate: 9600"  + "\n"
        if bits_2[4:8] == '0111':
            setupstring += "Baud rate: 300"  + "\n"

        bits_3 = (bin(int(byte3,16))[2:]).zfill(8)
        #print bits_3
        #print bits_3[0]

        setupstring += "Channel 3 enabled\n" if bits_3[0] == '1' else "Channel 3 disabled\n"
        setupstring += "Channel 2 enabled\n" if bits_3[1] == '1' else "Channel 2 disabled\n"
        setupstring += "Channel 1 enabled\n" if bits_3[2] == '1' else "Channel 1 disabled\n"
        setupstring += "No cold junction compensation\n" if bits_3[3] == '1' else "Cold junction compensation enabled\n"
        setupstring += "Unit: Fahrenheit\n" if bits_3[4] == '1' else "Unit: Celsius\n"

        #print (bin(int(byte4,16))[2:]).zfill(8)
        
        return setupstring
    
    def WriteEnable(self):
        self.f.write("$" + "1WE" + "\r")
        time.sleep(1)
        WE_string = self.f.read(self.f.inWaiting())
        returnstring = False
        if WE_string == '\x00*\r':
            returnstring = True
        return returnstring

    def RemoteReset(self):
        WE_string = self.WriteEnable()
        returnstring = False
        if WE_string == True:
            self.f.write("$" + "1RR" + "\r")
            time.sleep(1)
            RR_string = self.f.read(self.f.inWaiting())
            if RR_string == '\x00*\r':
                returnstring = True
        return returnstring

    def StandardSettings(self):
        returnstring = False
        if self.WriteEnable() == True:
            self.f.write("$" + "1SU3102E942" + "\r")
            #self.f.write("$" + "1SU3107E142" + "\r")#factory reset, remember to change if sentence
            time.sleep(1)
            if self.f.read(self.f.inWaiting()) == '\x00*\r': #'\x00*3102E142\r':
                print 'remove grounding of default terminal'
                if self.RemoteReset() == True:
                    returnstring = True
                    time.sleep(10)
        return returnstring

    def ChangeTemperatureScale(self,scale):
        if not (scale=='f' or scale=='c'):
            return(False)

if __name__ == "__main__":
    omega = OmegaBus('/dev/ttyUSB0')
    #print 'changing settings: ' + str(omega.StandardSettings())
    #print 'Temperature, channel 0 : ' + str(omega.ReadValue(0))
    print 'Temperature, channel 1 : ' + str(omega.ReadValue(1))
    print 'Temperature, channel 2 : ' + str(omega.ReadValue(2))
    print 'Temperature, channel 3 : ' + str(omega.ReadValue(3))
    print 'Temperature, channel 4 : ' + str(omega.ReadValue(4))
    #print 'Temperature, channel 5 : ' + str(omega.ReadValue(5))
    #print 'Min, channel 0 : ' + str(omega.ReadMin(0))
    #print 'Max, channel 0 : ' + str(omega.ReadMax(0))
    print 'Setup : \n' + str(omega.ReadSetup())

    #print ChangeTemperatureScale('f')
