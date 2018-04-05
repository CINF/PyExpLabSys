""" Driver for MKS 925 micro pirani """
from __future__ import print_function
import time
import logging
import serial
from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

class Mks925(object):
    """ Driver for MKS 925 micro pirani """
    def __init__(self, port):
        self.ser = serial.Serial(port, 9600, timeout=2)
        time.sleep(0.1)

    def comm(self, command):
        """ Implement communication protocol """
        prestring = b'@254'
        endstring = b';FF'
        self.ser.write(prestring + command.encode('ascii') + endstring)
        time.sleep(0.3)
        return_string = self.ser.read(self.ser.inWaiting()).decode()
        return return_string

    def read_pressure(self):
        """ Read the pressure from the device """
        command = 'PR1?'
        error = 1
        while (error > 0) and (error < 10):
            signal = self.comm(command)
            signal = signal[7:-3]
            try:
                value = float(signal)
                error = 0
            except ValueError:
                error = error + 1
                value = -1.0
        return value

    def set_comm_speed(self, speed):
        """ Change the baud rate """
        command = 'BR!' + str(speed)
        signal = self.comm(command)
        return signal

    def change_unit(self, unit): #STRING: TORR, PASCAL, MBAR
        """ Change the unit of the return value """
        command = 'U!' + unit
        signal = self.comm(command)
        return signal

    def read_serial(self):
        """ Read the serial number of the device """
        command = 'SN?'
        signal = self.comm(command)
        signal = signal[7:-3]
        return signal

if __name__ == '__main__':
    MKS = Mks925('/dev/ttyUSB1')
    #print MKS.set_comm_speed(9600)
    print(MKS.change_unit('MBAR'))
    print("Pressure: " + str(MKS.read_pressure()))
    print('Serial: ' + str(MKS.read_serial()))
