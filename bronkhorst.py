import serial
import time

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
    print pressure
