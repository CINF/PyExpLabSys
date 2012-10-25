import serial
import time

f = serial.Serial('/dev/ttyUSB0',9600)
time.sleep(0.1)

f.write("$1RD" + "\r")
time.sleep(0.1)
print f.read(f.inWaiting())

f.write("$1RS" + "\r")
time.sleep(0.1)
print f.read(f.inWaiting())

"""
f.write("$1WE" + "\r")
time.sleep(2)
print f.read(f.inWaiting())

f.write("#1SU3102E142" + "\r")
time.sleep(2)
print f.read(f.inWaiting())

f.write("$1RS" + "\r")
time.sleep(2)
print f.read(f.inWaiting())

f.write("$1WE" + "\r")
time.sleep(2)
print f.read(f.inWaiting())

f.write("$1RR" + "\r")
time.sleep(2)
print f.read(f.inWaiting())
"""

f.close()
