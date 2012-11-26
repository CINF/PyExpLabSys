import serial
import time
import threading
import Queue
import time
from datetime import datetime
import serial
import sys
#sys.path.append('../')
import MySQLdb

#ser = serial.Serial('/dev/ttyUSB0',300)
#print 'NGC2D port 0'
#ser=serial.Serial(
#            #port=port,
#            port='/dev/ttyUSB0',
#            baudrate=9600,
#            parity=serial.PARITY_NONE,
#            stopbits=serial.STOPBITS_ONE,
#            bytesize=serial.EIGHTBITS,
#            xonxoff=False
#            )
#time.sleep(1.0)
#string='*P0'
#print 'write string: ' + string
#ser.write(string)
#time.sleep(1.0)
#temp_string = ser.read(ser.inWaiting())
#print 'output string: ' + temp_string
#ser.close()
#print ' '

print 'NGC2D port 1'
ser=serial.Serial(
            #port=port,
            port='/dev/ttyUSB1',
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            xonxoff=False
            )
time.sleep(1.0)
string='*P0'
print 'write string: ' + string
ser.write(string)
time.sleep(1.0)
temp_string = ser.read(ser.inWaiting())
print 'output string: ' + temp_string
print 'Length: ' + str(len(temp_string))
ser.close()
print ' '

print 'OmegaBus port 0'
ser = serial.Serial('/dev/ttyUSB0',300)
time.sleep(1.0)
string='$' + str(1) + 'RD' + '\r'
print 'write string: ' + string
ser.write(string)
time.sleep(1.0)
temp_string = ser.read(ser.inWaiting())
print 'output string: ' + temp_string
ser.close()
print ' '

#print 'OmegaBus port 1'
#ser = serial.Serial('/dev/ttyUSB1',300)
#time.sleep(0.1)
#string='$' + str(1) + 'RD' + '\r'
#print 'write string: ' + string
#ser.write(string)
#time.sleep(1.0)
#temp_string = ser.read(ser.inWaiting())
#print 'output string: ' + temp_string
#ser.close()
#print ' '
