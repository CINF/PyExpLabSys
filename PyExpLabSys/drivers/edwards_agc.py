""" Driver and simple test case for Edwards Active Gauge Controler """
from __future__ import print_function
import serial

class EdwardsAGC(object):
    """ Primitive driver for Edwards Active Gauge Controler
    Complete manual found at
    http://www.idealvac.com/files/brochures/Edwards_AGC_D386-52-880_IssueM.pdf """
    def __init__(self, port='/dev/ttyUSB0'):
        self.serial = serial.Serial(port, baudrate=9600, timeout=0.5)

    def comm(self, command):
        """ Implements basic communication """
        comm = command + "\r"
        for _ in range(0, 10): # Seems you no to query several times to get correct reply
            self.serial.write(comm.encode('ascii'))
            complete_string = self.serial.readline().decode()
        self.serial.write(comm.encode('ascii'))
        complete_string = self.serial.readline().decode()
        complete_string = complete_string.strip()
        return complete_string

    def gauge_type(self, gauge_number):
        """ Return the type of gauge """
        types = {0: 'Not Fitted', 1: '590 CM capacitance manometer',
                 20: 'Wide range gauge'} # Feel free to fill in....

        type_number = int(self.comm('?GV ' + str(gauge_number)))
        gauge_type = types[type_number]
        return gauge_type

    def software_version(self):
        return self.comm('?VE')
    
if __name__ == '__main__':
    E_AGC = EdwardsAGC()
    print(E_AGC.gauge_type(1))
    print(E_AGC.comm('?GA 1'))
    print(E_AGC.comm('?GA 2'))
    print(E_AGC.comm('?GA 3'))
    print(E_AGC.software_version())
