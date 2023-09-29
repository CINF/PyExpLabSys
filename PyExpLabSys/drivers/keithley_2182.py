""" Simple driver for Keithley 2182 Nanovolt Meter """
from PyExpLabSys.drivers.scpi import SCPI


class Keithley2182(SCPI):
    """
    Simple driver for Keithley 2182 Nanovolt Meter
    Actual implementation performed on a 2182a - please
    double check if you have a 2182.
    """

    def __init__(
        self, interface, hostname='', device='', baudrate=9600, gpib_address=None
    ):
        if interface == 'serial':
            SCPI.__init__(
                self,
                interface=interface,
                device=device,
                baudrate=baudrate,
                line_ending='\n',
            )
            self.comm_dev.timeout = 2
            self.comm_dev.rtscts = False
            self.comm_dev.xonxoff = False
        if interface == 'gpib':
            SCPI.__init__(self, interface=interface, gpib_address=gpib_address)

        # For now, turn off continous trigger - this might need reconsideration
        self.scpi_comm('INIT:CONT OFF')

    def set_range(self, channel1: float = None, channel2: float = None):
        """
        Set the measurement range of the device, 0 will indicate auto-range
        """
        if channel1 is not None:
            if channel1 > 120:
                channel1 = 120
            if channel1 == 0:
                self.scpi_comm(':SENSE:VOLT:CHANNEL1:RANGE:AUTO ON')
            else:
                self.scpi_comm(':SENSE:VOLT:CHANNEL1:RANGE {:.2f}'.format(channel1))

        if channel2 is not None:
            if channel2 > 12:
                channel2 = 12
            if channel2 == 0:
                self.scpi_comm(':SENSE:VOLTAGE:CHANNEL2:RANGE:AUTO ON')
            else:
                self.scpi_comm(':SENSE:VOLT:CHANNEL2:RANGE {:.2f}'.format(channel2))

        actual_channel1_raw = self.scpi_comm(':SENSE:VOLTAGE:CHANNEL1:RANGE?')
        actual_channel2_raw = self.scpi_comm(':SENSE:VOLTAGE:CHANNEL2:RANGE?')
        range1 = float(actual_channel1_raw)
        range2 = float(actual_channel2_raw)
        return range1, range2

    def set_integration_time(self, nplc: float = None):
        """
        Set the measurement integration time
        """
        if nplc is not None:
            if nplc < 0.01:
                nplc = 0.01
            if nplc > 60:
                nplc = 60
            self.scpi_comm('SENSE:VOLTAGE:NPLCYCLES {}'.format(nplc))
        current_nplc = float(self.scpi_comm('SENSE:VOLTAGE:NPLCYCLES?'))
        return current_nplc

    def read_voltage(self, channel: int):
        """ Read the measured voltage """
        if channel not in (1, 2):
            return None
        self.scpi_comm(":SENSE:FUNC 'VOLT:DC'")
        self.scpi_comm(':SENSE:CHANNEL {}'.format(channel))
        raw = self.scpi_comm(':READ?')
        voltage = float(raw)
        return voltage


if __name__ == '__main__':
    GPIB = 7
    NVM = Keithley2182(interface='gpib', gpib_address=GPIB)

    print(NVM.set_range(1, 0.01))
    print(NVM.set_integration_time(10))

    for i in range(0, 10):
        print()
        print('Channel 1: {:.3f}uV'.format(NVM.read_voltage(1) * 1e6))
        print('Channel 2: {:.3f}uV'.format(NVM.read_voltage(2) * 1e6))
