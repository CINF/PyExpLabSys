""" Simple driver for Keithley 6220 SMU """
import time
from PyExpLabSys.drivers.scpi import SCPI


class Keithley6220(SCPI):
    """
    Simple driver for Keithley 6200 SMU
    Actual implementation performed on a 6221 - please
    double check if you have a 6220.
    """

    def __init__(self, interface, hostname='', device='',
                 baudrate=9600, gpib_address=None):
        if interface == 'serial':
            SCPI.__init__(self, interface=interface, device=device,
                          baudrate=baudrate, line_ending='\n')
            self.comm_dev.timeout = 2
            self.comm_dev.rtscts = False
            self.comm_dev.xonxoff = False
        if interface == 'lan':
            SCPI.__init__(self, interface=interface, hostname=hostname)
        if interface == 'gpib':
            SCPI.__init__(self, interface=interface, gpib_address=gpib_address)

    def output_state(self, output_state: bool = None):
        """ Turn the output on or off """
        if output_state is not None:
            if output_state:
                self.scpi_comm('OUTPUT ON')
            else:
                self.scpi_comm('OUTPUT OFF')
        actual_state_raw = self.scpi_comm('OUTPUT?')
        actual_state = int(actual_state_raw[0]) == 1
        return actual_state

    def set_current_range(self, current_range=None):
        """
        This device can only source current, not voltage
        """
        print('TODO: RANGE IS HARD-CODED!')
        # uA range
        self.scpi_comm('CURRENT:RANGE 12e-6')

    def set_voltage_limit(self, voltage: float = None):
        """ Set the desired voltate limit """
        if voltage is not None:
            self.scpi_comm('CURRENT:COMPLIANCE {:.9f}'.format(voltage))
        actual = self.scpi_comm('CURRENT:COMPLIANCE?')
        return actual

    def set_current(self, current: float):
        """ Set the DC current, when not performing a waveform """
        self.scpi_comm('CURRENT {:.9f}'.format(current))
        return True

    def source_sine_wave(self, frequency, amplitude):
        self.scpi_comm('SOUR:WAVE:FUNC SIN')
        self.scpi_comm('SOUR:WAVE:FREQ {}'.format(frequency))
        self.scpi_comm('SOUR:WAVE:AMPL {}'.format(amplitude))
        self.scpi_comm('SOUR:WAVE:OFFS 0')  # Offset
        # self.scpi_comm('SOUR:WAVE:PMAR:STAT OFF')  !!!! ‘ Turn off phase marker.
        self.scpi_comm('SOUR:WAVE:DUR:TIME INF')
        self.scpi_comm('SOUR:WAVE:RANG BEST')
        self.scpi_comm('SOUR:WAVE:ARM')
        self.scpi_comm('SOUR:WAVE:INIT')

    def stop_and_unarm(self):
        self.scpi_comm('SOUR:WAVE:ABOR')


if __name__ == '__main__':
    GPIB = 12
    SMU = Keithley6220(interface='gpib', gpib_address=GPIB)
    print(SMU.set_voltage_limit(2))
    SMU.set_current_range()
    # SMU.set_current(1e-9)

    SMU.source_sine_wave(700, 4e-7)
    time.sleep(1)
    print(SMU.scpi_comm('CURRENT?'))

    time.sleep(10)
    SMU.stop_and_unarm()
