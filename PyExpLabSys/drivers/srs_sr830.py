""" Simple driver for Keithley SRS SR830 Lock-In Amplifier """
import time
from PyExpLabSys.drivers.scpi import SCPI


class SR830(SCPI):
    """
    Simple driver for SRS SR830
    """

    def __init__(self, interface, gpib_address=None):
        if interface == 'gpib':
            SCPI.__init__(self, interface=interface,
                          gpib_address=gpib_address, line_ending='\n')
            self.comm_dev.clear()
            time.sleep(0.2)

    def use_external_reference(self, trigger: str):
        """
        Configures the reference frequency to be externally generated,
        the trigger can take the values sine, rising and falling.
        """
        if trigger == 'sine':
            param = 0
        elif trigger == 'rising':
            param = 1
        elif trigger == 'falling':
            param = 2
        else:
            return False

        self.scpi_comm('FMOD 0')  # Set frequency reference to internal
        self.scpi_comm('RSLP {}'.format(param))
        return True

    def use_internal_freq_reference(self, frequency: float, amplitude: float = 1):
        self.scpi_comm('FMOD 1')  # Set frequency reference to internal
        self.scpi_comm('FREQ {}'.format(frequency))
        self.scpi_comm('SLVL {}'.format(amplitude))

    def read_x_and_y(self):
        """
        Returns the x and y values as well as the reference frequency.
        """
        value_raw = self.scpi_comm('SNAP? 1, 2, 9')
        values = value_raw.split(',')
        x = float(values[0])
        y = float(values[1])
        freq = float(values[2])
        return x, y, freq

    def read_r_and_theta(self):
        """
        Returns the r and theta values as well as the reference frequency.
        """
        value_raw = self.scpi_comm('SNAP? 3, 4, 9')
        values = value_raw.split(',')
        r = float(values[0])
        theta = float(values[1])
        freq = float(values[2])
        return r, theta, freq


if __name__ == '__main__':
    LockIn = SR830('gpib', 8)
    LockIn.use_internal_freq_reference(500.0)
    time.sleep(1)
    for i in range(0, 10):
        print(LockIn.read_x_and_y())
    print()
    for i in range(0, 10):
        print(LockIn.read_r_and_theta())
