import telnetlib
import time

from scpi import SCPI

class KeithleySMU(SCPI):

    def __init__(self):
        SCPI.__init__(self, '/dev/ttyS0', 'serial')
        self.f.baudrate = 19200
        self.f.timeout = 5

    def channel_name(self, channel):
        if channel == 1:
            ch = 'a'
        if channel == 2:
            ch = 'b'
        return(ch)
    
    def read_current(self, channel=1):
        ch = self.channel_name(channel)
        self.scpi_comm('reading = smu' + ch + '.measure.i()')
        self.scpi_comm('*TRG')
        return(float(self.scpi_comm('print(reading)', True)))

    def read_voltage(self, channel=1):
        ch = self.channel_name(channel)
        self.scpi_comm('reading = smu' + ch + '.measure.v()')
        self.scpi_comm('*TRG')
        return(float(self.scpi_comm('print(reading)', True)))

if __name__ == '__main__':
    smu = KeithleySMU()
    print smu.read_software_version()
    print smu.read_current()
    print smu.read_voltage()
