""" Driver for ISO-TECH IPS power supply series

It has not been possible to get the device to give any
meaningfull replys, but actually setting output values
works.
"""
import serial
import time

class IPS(object):
    """ Driver for IPS power supply """
    def __init__(self, port):
        self.serial = serial.Serial(port, 2400, timeout=10, xonxoff=False,
                                    rtscts=False)

    def comm(self, command):
        """ Communicate with instrument """
        encoded_command = (command + '\r').encode('ascii')
        self.serial.write(encoded_command)
        # The unit will fail to run at more than 2Hz
        time.sleep(0.5)
        return True

    def set_vlimit_to_max(self):
        """ Set the voltage limit to the maximum the device deliver """
        self.comm('SUM')

    def set_ilimit_to_max(self):
        """ Set the current limit to the maximum the device deliver """
        self.comm('SIM')

    def set_relay_status(self, status=False):
        """ Turn the output on or off """
        if status is True:
            self.comm('KOE')
        else:
            self.comm('KOD')

    def set_output_voltage(self, voltage):
        """ Set the output voltage """
        self.comm('SV ' + '{:2.2f}'.format(voltage).zfill(5))

    def set_voltage_limit(self, voltage):
        """ Set the voltage limit """
        self.comm('SU ' + str(voltage))

    def set_current_limit(self, current):
        """ Set the current limit """
        self.comm('SI ' + '{:1.2f}'.format(current).zfill(3))

if __name__ == '__main__':
    ips = IPS('/dev/ttyUSB2')
    ips.set_relay_status(True)
    ips.set_output_voltage(5)
