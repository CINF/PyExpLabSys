""" Simple driver for Keithley SMU """
from __future__ import print_function
import time
import logging
from PyExpLabSys.drivers.scpi import SCPI
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class KeithleySMU(SCPI):
    """ Simple driver for Keithley SMU """

    def __init__(self, interface, hostname='', device=''):
        if interface == 'serial':
            SCPI.__init__(self, interface=interface, device=device, baudrate=19200)
            self.f.timeout = 5
        if interface == 'lan':
            SCPI.__init__(self, interface=interface, hostname=hostname)
        self.channel_names = {1: 'a', 2: 'b'}

    def output_state(self, output_on=False, channel=1):
        """ Turn the output on or off """
        if output_on is True:
            self.scpi_comm('smu' + self.channel_names[channel] + '.source.output = 1')
        else:
            self.scpi_comm('smu' + self.channel_names[channel] + '.source.output = 0')
        return output_on

    def read_current(self, channel=1):
        """ Read the measured current """
        self.scpi_comm('reading = smu' + self.channel_names[channel] + '.measure.i()')
        self.scpi_comm('*TRG')
        current_string = self.scpi_comm('print(reading)', True)
        try:
            current = float(current_string)
        except (ValueError, TypeError):
            current = None
            logging.error('Current string: ' + str(current_string))
        return current

    def read_voltage(self, channel=1):
        """ Read the measured voltage """
        self.scpi_comm('reading = smu' + self.channel_names[channel] + '.measure.v()')
        self.scpi_comm('*TRG')
        voltage_string = self.scpi_comm('print(reading)', True)
        try:
            voltage = float(voltage_string)
        except (ValueError, TypeError):
            voltage = None
            logging.error('Voltage string: ' + str(voltage_string))
        return voltage

    def set_voltage(self, voltage, channel=1):
        """ Set the desired voltage """
        self.scpi_comm('smu' + self.channel_names[channel] +
                       '.source.levelv = ' + str(voltage))
if __name__ == '__main__':
    PORT = '/dev/serial/by-id/'
    PORT += 'usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'

    SMU = KeithleySMU(interface='serial', device=PORT)
    print(SMU)
    SMU.set_voltage(0.24)
    time.sleep(1)
    print(SMU.read_software_version())
    print(SMU.read_current())
    print(SMU.read_voltage())
