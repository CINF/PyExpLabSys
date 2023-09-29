""" Simple driver for Keithley SRS SR830 Lock-In Amplifier """
import time
from PyExpLabSys.drivers.scpi import SCPI


class SR830(SCPI):
    """
    Simple driver for SRS SR830
    """

    def __init__(self, interface, gpib_address=None, device=None):
        if interface == 'serial':
            SCPI.__init__(self, interface=interface, device=device)
            time.sleep(0.2)
        if interface == 'gpib':
            SCPI.__init__(
                self, interface=interface, gpib_address=gpib_address, line_ending='\n'
            )
            self.comm_dev.clear()
            time.sleep(0.2)

    def use_external_reference(self, trigger: str):
        """
        Configures the reference frequency to be externally generated,
        the trigger can take the values sine, rising and falling.
        """
        # Todo: Returning False in an if-structure is not good practice
        # consider clean this up!
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

    def sensitivity(self, sensitivity: int = None):
        """
         0: 2 nV/fA       1: 5 nV/fA         2: 10 nV/fA       3: 20 nV/fA
         4: 50 nV/fA      5: 100 nV/fA       6: 200 nV/fA      7: 500 nV/fA
         8: 1µV/pA        9: 2µV/pA         10: µV/pA         11: µV/pA
        12: µV/pA        13: 50 µV/pA       14: 100 µV/pA     15: 200 µV/pA
        16: 500 µV/pA    17: 1 mV/n         18: 2 mV/nA       19: 5 mV/nA
        20: 10 mV/nA     21: 20 mV/nA       22: 50 mV/nA      23: 100 mV/nA
        24: 200 mV/nA    25: 500 mV/nA      26: 1 V/µA
        """
        print(self.scpi_comm('SENS?'))

    def time_constant(self, time_constant: int = None):
        """
         0: 10 µs         1: 30 µs           2: 100 µs         3: 300 µs
         4: 1 ms          5: 3 ms            6: 10 ms          7: 30 ms
         8: 100 ms        9: 300 ms         10: 1s            11: 3s
        12: 10 s         13: 30 s           14: 100 s         15: 300 s
        16: 1 ks         17: 3 ks           18: 10 ks         19: 30 ks
        """
        print(self.scpi_comm('OFLT?'))

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
    # LockIn = SR830('gpib', 8)
    # LockIn.sensitivity()

    LockIn = SR830('serial', device='/dev/ttyUSB1')
    print(LockIn.read_software_version())

    exit()

    LockIn.use_internal_freq_reference(500.0)
    time.sleep(1)
    for i in range(0, 10):
        print(LockIn.read_x_and_y())
    print()
    for i in range(0, 10):
        print(LockIn.read_r_and_theta())
