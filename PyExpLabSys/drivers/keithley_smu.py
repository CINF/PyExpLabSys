""" Simple driver for Keithley SMU """
import time
import logging
from scpi import SCPI

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
        return(voltage)

if __name__ == '__main__':
    smu = KeithleySMU(interface='serial',
                      device='/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0')
    print smu
    time.sleep(1)
    print smu.read_software_version()
    error = 0
    i = 0
    while error < 5000:
        i = i + 1
        smu = KeithleySMU(interface='serial', device='/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0')
        print i
        current = smu.read_current() 
        if current is not None:
            print('Current: ' + str(current) + 'Error: ' + str(error))
        else:
            error = error + 1
            logging.error('Error: ' + str(error))
            time.sleep(0.1)
            smu = KeithleySMU(interface='serial', device='/dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0')
            logging.error(smu)
 
