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
                 15: 'Active strain gauge', 5: 'Pirani L low pressure',
                 20: 'Wide range gauge'} # Feel free to fill in....

        type_number = int(self.comm('?GV ' + str(gauge_number)))
        gauge_type = types[type_number]
        return gauge_type

    def read_pressure(self, gauge_number):
        """ Read the pressure of a gauge """
        pressure_string = self.comm('?GA ' + str(gauge_number))
        pressure_value = float(pressure_string)
        return pressure_value

    def pressure_unit(self, gauge_number):
        """ Read the unit of a gauge """
        units = {0: 'mbar', 1: 'torr'}
        unit_string = self.comm('?NU ' + str(gauge_number))
        unit_number = int(unit_string)
        unit = units[unit_number]
        return unit

    def current_error(self):
        """ Read the current error code """
        error_code = self.comm('?SY')
        return error_code
    
    def software_version(self):
        """ Return the software version of the controller """
        return self.comm('?VE')
    
if __name__ == '__main__':
    E_AGC = EdwardsAGC()
    print(E_AGC.gauge_type(4))
    print(E_AGC.read_pressure(1))
    print(E_AGC.read_pressure(2))
    print(E_AGC.read_pressure(3))
    print(E_AGC.read_pressure(4))
    print(E_AGC.pressure_unit(1))
    print(E_AGC.current_error())

