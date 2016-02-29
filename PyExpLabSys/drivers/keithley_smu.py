""" Simple driver for Keithley SMU """
import time
from scpi import SCPI

class KeithleySMU(SCPI):
    """ Simple driver for Keithley SMU """

    def __init__(self, interface, hostname='', device=''):
        if interface == 'serial':
            SCPI.__init__(self, interface=interface, device=device)
            self.f.baudrate = 19200
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
        finished = False
        while not finished:
            try:
                current = float(self.scpi_comm('print(reading)', True))
                finished = True
            except ValueError:
                pass
        return current

    def read_voltage(self, channel=1):
        """ Read the measured voltage """
        self.scpi_comm('reading = smu' + self.channel_names[channel] + '.measure.v()')
        self.scpi_comm('*TRG')
        return(float(self.scpi_comm('print(reading)', True)))

if __name__ == '__main__':
    smu = KeithleySMU()
    print smu.read_software_version()
    print smu.read_current()
    print smu.read_voltage()
