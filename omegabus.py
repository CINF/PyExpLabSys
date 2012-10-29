import serial
import time

class OmegaBus():

    def __init__(self):
        self.f = serial.Serial('/dev/ttyUSB0',9600)
        time.sleep(0.1)

    def ReadValue(self,channel):
        self.f.write("$" + str(channel) + "RD" + "\r")
        time.sleep(0.1)
        temp_string = self.f.read(self.f.inWaiting())
        if temp_string[1] == "*":
            temp_string = temp_string[3:]
        return float(temp_string)

if __name__ == "__main__":
    omega = OmegaBus()
    print omega.ReadValue(1)
