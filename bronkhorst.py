import serial
import time
import threading

class Bronkhorst(threading.Thread):
    
    def __init__(self,port):
        ser = serial.Serial(port,38400)
        time.sleep(0.1)

    def comm(self,command):
        self.ser.write(command)
        time.sleep(0.1)
        return_string = self.ser.read(self.ser.inWaiting())
        return return_string

    def read_setpoint(self):
        read_setpoint = ':06030401210121\r\n' # Read setpoint
        val = self.comm(read_setpoint)
        val = [-6:]
        num = int(val,16)
        setpoint = range * num / 32000
        return setpoint

    def read_pressure(self):
        read_pressure = ':06030401210120\r\n' # Read pressure
        val = self.comm(read_pressure)
        val = [-6:]
        num = int(val,16)
        pressure = 2.5 * num / 32000
        return pressure

    def set_setpoint(self,setpoint,range):
        setpoint = setpoint / range * 32000
        setpoint = hex(setpoint)
        setpoint = '%setpoint' % 255
        set_setpoint = ':0603010121' + setpoint + '\r\n' #Set setpoint
        response = self.comm(set_setpoint)
        
if __name__ == '__main__':
    bh = Bronkhorst('/dev/ttyUSB0')
    print str( bh.read_setpoint())



        
'''
f = serial.Serial('/dev/ttyS0',38400)

a = ':06030401210121\r\n' # Read setpoint
b = ':06030401210120\r\n' # Read pressure

for i in range(0,50):
    f.write(b)
    time.sleep(0.1)
    val = f.read(f.inWaiting())
    val = val[-6:]
    num =  int(val,16)
    pressure = 2.5 * num / 32000
    print pressure '''
