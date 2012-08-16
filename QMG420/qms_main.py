import serial
import time


class QMS:

    def __init__(self):
        self.device = '/dev/ttyUSB0'

    def comm(self,command,read=False):
        f = serial.Serial()
        f.baudrate = 9600
        f.xonxoff = True
        f.port = self.device
        f.timeout = 1
        f.open()
        f.write(command + '\r')

        time.sleep(0.01)
        return_string = ""    
        if read:
            return_string = f.readline()
        f.close()
        return return_string



   

ms = QMS()
print ms.comm('STW',True)

#WriteCommand(f,'STW')
#print f.readline()

#time.sleep(0.1)

#CHM 0: SCAN-N
#CHM 1: SCAN-F
#CHM 2: SAMP-N
#CHM 3: PEAK-L
#CHM 4: PEAK-F
#command = 'CHM 2' + '\r'
#f.write(command)

#WIDTH: WID
#RESOLUTION: RES (0...255)

#command = 'FIR 28.00' + '\r'
#f.write(command)


#Speed (0..15)
#command = 'SPE 9' + '\r'
#f.write(command)

#command = 'RES 0' + '\r'
#f.write(command)

#Range 0..7 (1e-5...1e-12)
#command = 'RAN 5' + '\r'
#f.write(command)

#Filter, 0=auto
#command = 'FIL 0' + '\r'
#f.write(command)


#command = 'RUN' + '\r'
#f.write(command)

#time.sleep(2)

#command = 'HEA' + '\r'
#f.write(command)

#print f.readline()

#for i in range(0,4):
#	command = chr(5) + '\r'
#	f.write(command)
#
#	print f.readline()

#command = 'FIR 27.00' + '\r'
#f.write(command)

#time.sleep(2)

#command = 'HEA' + '\r'
#f.write(command)

#print f.readline()

#for i in range(0,4):
#	command = chr(5) + '\r'
#	f.write(command)
#
#	print f.readline()





#f.close()