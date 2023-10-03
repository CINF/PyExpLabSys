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
            self.line_ending = '\r'
            self.comm_dev.xonxoff = False
            self.comm_dev.flush()
            waiting = self.comm_dev.inWaiting()
            self.comm_dev.read(waiting)
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

    def use_internal_freq_reference(self, frequency: float, amplitude: float = None):
        self.scpi_comm('FMOD 1')  # Set frequency reference to internal
        self.scpi_comm('FREQ {}'.format(frequency))
        if amplitude is not None:
            self.scpi_comm('SLVL {}'.format(amplitude))

    def sensitivity(self, sensitivity: int = None):
        """
         0: 2nV     1: 5 nV     2: 10nV    3: 20 n    4: 50nV    5: 100 nV
         6: 200nV   7: 500nV    8: 1µV     9: 2µV    10: 5µV    11: 10µV
        12: 20µV   13: 50µV    14: 100µV  15: 200µV  16: 500µV  17: 1mV
        18: 2mV    19: 5mV     20: 10mV   21: 20mV   22: 50mV   23: 100mV
        24: 200mV  25: 500mV   26: 1 V
        """
        sensitivity_table = {
            0:  2e-9,  1: 5e-9,  2: 1e-8,  3: 2e-8,  4: 5e-8,  5: 1e-7,
            6:  2e-7,  7: 5e-7,  8: 1e-6,  9: 2e-6, 10: 5e-6, 11: 1e-5,
            12: 2e-5, 13: 5e-5, 14: 1e-4, 15: 2e-4, 16: 5e-4, 17: 1e-3, 
            18: 2e-3, 19: 5e-3, 20: 1e-2, 21: 2e-2, 22: 5e-2, 23: 0.1,
            24: 0.2,  25: 0.5,  26: 1
        }
        sensitivity_index = self.scpi_comm('SENS?')
        sensitivity = sensitivity_table[int(sensitivity_index)]
        return sensitivity

    def time_constant(self, time_constant: int = None):
        """
         0: 10 µs         1: 30 µs           2: 100 µs         3: 300 µs
         4: 1 ms          5: 3 ms            6: 10 ms          7: 30 ms
         8: 100 ms        9: 300 ms         10: 1s            11: 3s
        12: 10 s         13: 30 s           14: 100 s         15: 300 s
        16: 1 ks         17: 3 ks           18: 10 ks         19: 30 ks
        """
        time_constant_table = {
            0: 1e-5, 1: 3e-5, 2: 1e-4, 3: 3e-4, 4: 1e-3, 5: 3e-3,
            6: 1e-2, 7: 3e-2, 8: 0.1,  9: 0.3,  10: 1, 11: 3,
            12: 10, 13: 30, 14: 1e2, 15: 3e2, 16: 1e3, 17: 3e4,
            18: 1e4, 19: 3e4
        }
        time_index = self.scpi_comm('OFLT?')
        time_constant = time_constant_table[int(time_index)]
        return time_constant

    def reserve_configuration(self):
        reserve_raw = self.scpi_comm('RMOD?')
        if int(reserve_raw) == 0:
            reserve = 'High'
        elif int(reserve_raw) == 1:
            reserve = 'Normal'
        elif int(reserve_raw) == 2:
            reserve = 'Low Noise'
        return reserve

    def filter_slope(self):
        # Slope unit: dB/oct
        slope_raw = self.scpi_comm('OFSL?')
        if int(slope_raw) == 0:
            slope = 6
        elif int(slope_raw) == 1:
            slope = 12
        elif int(slope_raw) == 2:
            slope = 18
        elif int(slope_raw) == 3:
            slope = 24
        return slope

    def input_configuration(self):
        """
        Read the combined input configuration
        """
        input_config_raw = self.scpi_comm('ISRC?')
        if int(input_config_raw) == 0:
            config = 'A'
        elif int(input_config_raw) == 1:
            config = 'A-B'
        elif int(input_config_raw) == 2:
            config = 'I 1Mohm'
        elif int(input_config_raw) == 3:
            config = 'I 100Mohm'

        ground_config_raw = self.scpi_comm('IGND?')
        if int(ground_config_raw) == 0:
            grounding = 'Float'
        elif int(ground_config_raw) == 1:
            grounding = 'Ground'

        input_coupling_raw = self.scpi_comm('ICPL?')
        if int(input_coupling_raw) == 0:
            coupling = 'AC'
        elif int(input_coupling_raw) == 1:
            coupling = 'DC'

        summary = '{} - {} - {}'.format(config, grounding, coupling)
        input_config = {
            'config': config,
            'grounding': grounding,
            'coupling': coupling,
            'summary': summary
        }
        return input_config

    def read_x_and_y_noise(self):
        """
        Sets the display to noise measurement and reads the noise
        (that can only be read via reading the display value)
        Returns x_noise, y_noise, x, y
        """
        self.scpi_comm('DDEF 1,2,0')
        self.scpi_comm('DDEF 2,2,0')

        cmd = 'SNAP? 1, 2, 10, 11'
        value_raw = self.scpi_comm(cmd, expect_return=True)
        values = value_raw.split(',')
        x = float(values[0])
        y = float(values[1])
        x_noise = float(values[2])
        y_noise = float(values[3])
        return x_noise, y_noise, x, y

    def read_x_and_y(self):
        """
        Returns the x and y values as well as the reference frequency.
        """
        value_raw = self.scpi_comm('SNAP? 1, 2, 9', expect_return=True)
        values = value_raw.split(',')
        x = float(values[0])
        y = float(values[1])
        freq = float(values[2])
        return x, y, freq

    def read_r_and_theta(self):
        """
        Returns the r and theta values as well as the reference frequency.
        """
        value_raw = self.scpi_comm('SNAP? 3, 4, 9', expect_return=True)
        values = value_raw.split(',')
        r = float(values[0])
        theta = float(values[1])
        freq = float(values[2])
        return r, theta, freq

    def estimate_noise_at_frequency(self, frequency, threshold=0.02):
        msg = 'x_noise: {}, y_noise: {}, x: {}, y: {}'

        self.use_internal_freq_reference(frequency)
        time_constant = self.time_constant()
        # print('Time constant is: {}s'.format(time_constant))
        x_noise_old, _, _, _ = self.read_x_and_y_noise()

        while True:
            if x_noise_old == 0:
                return None
            time.sleep(time_constant * 50)
            x_noise, y_noise, x, y = self.read_x_and_y_noise()
            print(msg.format(x_noise, y_noise, x, y))
            ratio = x_noise / x_noise_old
            if (1 - threshold) < ratio < (1 + threshold):
                break
            x_noise_old = x_noise
        return x_noise, y_noise, x, y


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
