import serial
import time

class NGC2D_comm():
    def __init__(self, device):
        self.f = serial.Serial(
            port=device,
            #port='/dev/ttyUSB1',
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            xonxoff=False
            )
        time.sleep(1)

    def comm(self,command):
        if command == "Poll":
            comm = "*P0"
        elif command == "Control":
            comm = "*C0"
        elif command == "ResetError":
            comm = "*E0"
        elif command == "Status":
            comm = "*S0"
        else:
            print("Unknown Command")
            return(None)  # Remember to test for None return value

        self.f.write(comm)
        time.sleep(1)
        #number = self.f.inWaiting()
        complete_string = self.f.read(self.f.inWaiting())
        #self.f.close()
        #print complete_string
        return(complete_string)

    def ReadPressure(self):
        pressure_string = self.comm('Status')
        pressure = pressure_string.split("\r\n")[0][9:16]
        try:
            if pressure[0] == " ":
                print("Pressure Gauge is Off")
                return(-1)
        except:
            print(pressure)
        #print pressure
        return(pressure)


    def ReadPressureUnit(self):
        unit_string = self.comm("Status")
        unit_string = unit_string.split("\r\n")[0][17]
        if unit_string == "T":
            unit = "Torr"
        elif unit_string == "P":
            unit = "Pa"
        elif unit_string == "M":
            unit = "mBar"
        #print unit
        return(unit)

if __name__ == '__main__':
    NG = NGC2D_comm('/dev/ttyUSB1')
    print("Pressure: " + str(NG.ReadPressure()))
