import serial
import time

class NGC2D_comm
    def __init__(self,port):
        ser = serial.Serial(
            #port="/dev/ttyUSB0",
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            xonxoff=False
            )
        time.sleep(0.1)

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
            print "Unknown Command"
            return(None)  # Remember to test for None return value

        ser.write(comm)
        time.sleep(1)
        number = ser.inWaiting()
        complete_string = ser.read(number)
        ser.close()
        #print complete_string
        return(complete_string)

    def ReadPressure(self):
        command = 'Status'
        pressure_string = self.comm(command)
        pressure = pressure_string.split("\r\n")[0][9:16]
        if pressure[0] == " ":
            print "Pressure Gauge is Off"
            return(None)
        #print pressure
        return(float(pressure))


    def ReadPressureUnit(self):
        command = 'Status'
        unit_string = self.comm(command)
        unit_string = unit_string.split("\r\n")[0][17]
        if unit_string == "T":
            unit = "Torr"
        elif unit_string == "P":
            unit = "Pa"
        elif unit_string == "M":
            unit = "mBar"
        #print unit
        return(unit)

    #print "test"
    #print ReadPressure()
