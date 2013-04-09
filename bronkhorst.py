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
        setpoint = hex(int(setpoint))
        setpoint = setpoint.upper()
        setpoint = setpoint[2:].rstrip('L')
        set_setpoint = ':0603010121' + setpoint + '\r\n' # Set setpoint
        response = self.comm(set_setpoint)
        return str(response)

    def read_counter_value(self):
        read_counter = ':06030401210141\r\n'
        response = self.comm(read_counter)
        return str(response)

    def read_serial(self):
        read_serial = ':1A0304F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        response = self.comm(read_serial)
        response = response[13:-84]
        response = response.decode('hex')
        return str(response)

    def read_unit(self):
        read_capacity = ':1A0304F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        response = self.comm(read_capacity)
        response = response[77:-26]
        response = response.decode('hex')
        return str(response)

    def read_capacity(self):
        read_capacity = ':1A0304F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        response = self.comm(read_capacity)
        response = response[65:-44]
        #response = response.decode('hex')
        return str(response)

        
if __name__ == '__main__':
    bh = Bronkhorst('/dev/ttyUSB4')
    print bh.set_setpoint(5.0,10)
    print bh.read_serial()
    print bh.read_unit()
    print bh.read_capacity()
    #print bh.read_counter_value()
    #print str(bh.read_setpoint())
    #print str(bh.read_measure())
