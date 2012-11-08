import serial
import time

class AK_comm():

    def __init__(self,port)
        self.f = serial.SerialPort(port,9600,xonxoff=False,timeout=2



def NGC2D_comm(command):
    ser = serial.Serial(
        port=5,
        baudrate=9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        xonxoff=False
        ) 
