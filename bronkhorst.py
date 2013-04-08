import serial
import time
import threading

class Bronkhorst():
    
    def __init__(self,port):
        self.ser = serial.Serial(port,38400)
        time.sleep(0.1)

    def comm(self,command):
        self.ser.write(command)
        time.sleep(0.1)
        return_string = self.ser.read(self.ser.inWaiting())
        return return_string

    def read_setpoint(self):
        read_setpoint = ':06030401210121\r\n' # Read setpoint
        response = self.comm(read_setpoint)
        response = int(response[11:], 16)
        return str(response)

    def read_measure(self,max_flow):
        read_pressure = ':06030401210120\r\n' # Read pressure
        val = self.comm(read_pressure)
        val = val[-6:]
        num = int(val,16)
        pressure = max_flow * num / 32000.0
        return pressure

    def set_setpoint(self,setpoint,max_flow):
        setpoint = (setpoint / max_flow) * 32000.0
        print setpoint
        setpoint = hex(int(setpoint))
        setpoint = setpoint.upper()
        setpoint = setpoint[2:].rstrip('L')
        set_setpoint = ':0603010121' + setpoint + '\r\n' # Set setpoint
        response = self.comm(set_setpoint)
        return response
        
if __name__ == '__main__':
    bh = Bronkhorst('/dev/ttyUSB4')
    #bh.set_setpoint(5,10)
    #print str(bh.read_setpoint())
    print str(bh.read_measure())
