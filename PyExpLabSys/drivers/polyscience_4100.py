""" Driver and test case for Polyscience 4100 """
from __future__ import print_function
import serial
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class Polyscience4100(object):
    """ Driver for Polyscience 4100 chiller """
    def __init__(self, port='/dev/ttyUSB0'):
        self.ser = serial.Serial(port, 9600, timeout=0.5)
        self.max_setpoint = 30
        self.min_setpoint = 10
        assert self.min_setpoint < self.max_setpoint

    def comm(self, command):
        """ Send serial commands to the instrument """
        command = command + '\r'
        command = command.encode('ascii')
        self.ser.write(command)
        reply = self.ser.readline().decode()
        return reply[:-1]

    def set_setpoint(self, value):
        """ Set the temperature setpoint """
        if value > self.max_setpoint:
            value = self.max_setpoint
        if value < self.min_setpoint:
            value = self.min_setpoint

        string = '{0:.0f}'.format(value)
        if len(string) == 1:
            string = '00' + string
        else:
            string = '0' + string
        assert len(string) == 3
        value = self.comm('SS' + string)
        success = (value == '!')
        return success

    def turn_unit_on(self, turn_on):
        """ Turn on or off the unit """
        if turn_on is True:
            value = self.comm('SO1')
        if turn_on is False:
            value = self.comm('SO0')
        return value

    def read_setpoint(self):
        """ Read the current value of the setpoint """
        try:
            value = float(self.comm('RS'))
        except ValueError:
            value = float('NaN')
        return float(value)

    def read_unit(self):
        """ Read the measure unit """
        value = self.comm('RU')
        return value

    def read_temperature(self):
        """ Read the actual temperature of the water """
        try:
            status = self.comm('RW')
            if status == '1':
                value = float(self.comm('RT'))
            else:
                value = float('nan')
        except ValueError:
            value = float('nan')
        return value

    def read_pressure(self):
        """ Read the output pressure """
        try:
            status = self.comm('RW')
            if status == '1':
                value = float(self.comm('RK')) / 100.0
            else:
                value = float('nan')
        except ValueError:
            value = float('nan')
        return value

    def read_flow_rate(self):
        """ Read the flow rate """
        try:
            status = self.comm('RW')
            if status == '1':
                value = float(self.comm('RL'))
            else:
                value = float('nan')
        except ValueError:
            value = float('nan')
        return value

    def read_ambient_temperature(self):
        """ Read the ambient temperature in the device """
        try:
            status = self.comm('RW')
            if status == '1':
                value = float(self.comm('RA'))
            else:
                value = float('nan')
        except ValueError:
            value = float('nan')
        return value

    def read_status(self):
        """ Answers if the device is turned on """
        value = self.comm('RW')
        status = 'error'
        if value == '0':
            status = 'Off'
        if value == '1':
            status = 'On'
        return status

if __name__ == '__main__':
    CHILLER = Polyscience4100('/dev/ttyUSB0')
    print(CHILLER.read_status())

    print('Setpoint: {0:.1f}'.format(CHILLER.read_setpoint()))
    print('Temperature: {0:.1f}'.format(CHILLER.read_temperature()))
    print('Flow rate: {0:.2f}'.format(CHILLER.read_flow_rate()))
    print('Pressure: {0:.3f}'.format(CHILLER.read_pressure()))
    print('Status: ' + CHILLER.read_status())
    print('Ambient temperature: {0:.2f}'.format(CHILLER.read_ambient_temperature()))
