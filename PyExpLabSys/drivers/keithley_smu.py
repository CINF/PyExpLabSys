""" Simple driver for Keithley SMU """
from __future__ import print_function
import time
import logging
from PyExpLabSys.drivers.scpi import SCPI
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class KeithleySMU(SCPI):
    """ Simple driver for Keithley SMU """

    def __init__(self, interface, hostname='', device='', baudrate=19200):
        if interface == 'serial':
            SCPI.__init__(self, interface=interface, device=device, baudrate=baudrate)
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

    def iv_scan(self, v_from, v_to, stepsize, channel=1):
        """ Do an IV-scan """
        assert(v_from < v_to)
        assert(stepsize > 0)
        voltages = []
        currents = []
        current_voltage = v_from
        while current_voltage < v_to:
            self.set_voltage(current_voltage, channel)
            current = self.read_current(channel)
            voltages.append(current_voltage)
            currents.append(current)
            current_voltage +=stepsize
        return(voltages, currents)

    def set_current_limit(self, current, channel=1):
        """ Set the desired current limit """
        self.scpi_comm('smu' + self.channel_names[channel] +
                       '.source.limiti = ' + str(current))

    def set_voltage(self, voltage, channel=1):
        """ Set the desired voltage """
        self.scpi_comm('smu' + self.channel_names[channel] +
                       '.source.levelv = ' + str(voltage))

if __name__ == '__main__':
    PORT = '/dev/serial/by-id/'
    PORT += 'usb-1a86_USB2.0-Ser_-if00-port0'

    SMU = KeithleySMU(interface='serial', device=PORT, baudrate=9600)
    print(SMU)
    SMU.output_state(True)
    SMU.set_voltage(0.24)
    print(SMU.set_current_limit(1))
    time.sleep(1)
    print('-')
    print(SMU.read_software_version())
    print('-')
    print(SMU.read_current())
    print('-')
    print(SMU.read_voltage())
    print('-')
