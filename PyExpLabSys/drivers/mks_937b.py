""" Driver for MKS 937b gauge controller """
from __future__ import print_function
import time
import logging
import serial
from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

class Mks937b(object):
    """ Driver for MKS 937B Gauge Controller """
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
        success = return_string.find('ACK')
        if success > 0:
            return_string = return_string[success+3:-3]
        return return_string

    def read_pressure_gauge(self, gauge_number):
        """ Read a specific pressure gauge """
        pressure_string = self.comm('PR' + str(gauge_number) + '?')
        if pressure_string.find('LO') > -1:
            pressure_string = '0'
        if pressure_string.find('>') > -1:
            pressure_string = '-1'
        if pressure_string.find('OFF') > -1:
            pressure_string = '-1'
        if pressure_string.find('WAIT') > -1:
            pressure_string = '-1'
        pressure_value = float(pressure_string)
        return pressure_value

    def read_sensor_types(self):
        """ Return a list of connected sensors """
        sensors = self.comm('MT?')
        return sensors

    def read_all_pressures(self):
        """ Returns an overview of all sensors """
        return self.comm('PRZ?')

    def pressure_unit(self, unit=None):
        """ Read or configure pressure unit
        Legal values: torr, mbar, pascal, micron"""
        if unit is not None:
            self.comm('U!' + str(unit))
        unit = self.comm('U?')
        return unit

if __name__ == '__main__':
    MKS = Mks937b('/dev/ttyUSB0')
    print(MKS.read_pressure_gauge(1))
    print(MKS.read_pressure_gauge(3))
    print(MKS.read_pressure_gauge(5))
    print(MKS.read_all_pressures())
    print(MKS.read_sensor_types())
    print(MKS.pressure_unit('mbar'))
    #print(MKS.comm('PR1?'))
    #print(MKS.comm('PR2?'))
    #print MKS.set_comm_speed(9600)
    #print(MKS.change_unit('MBAR'))
    #print("Pressure: " + str(MKS.read_pressure()))
    #print('Serial: ' + str(MKS.read_serial()))
