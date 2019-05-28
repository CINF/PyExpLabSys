
"""Driver for the Analog Devices AD5667 2 channel analog output DAC

Implemented from the manual located `here
<http://www.analog.com/media/en/technical-documentation/data-sheets/AD5627R_5647R_5667R_
5627_5667.pdf>`__ and the examples located `here
<https://github.com/ControlEverythingCommunity/AD5667>`__.

"""

import time
import smbus
from PyExpLabSys.common.supported_versions import python3_only
python3_only(__file__)


class AD5667:

    """Driver for the Analog Devices AD5667 2 channel analog output DAC"""

    def __init__(self):
        """Initialize object properties"""
        # Get I2C bus
        self.bus = smbus.SMBus(1)

        self.address = 0x0E
        self.dac_and_input_register = {
            'both': 0x1F,
            'A': 0x18,
            'B': 0x19,
        }

        self.last_write = 0
        self.waittime = 0.1

    def write_to_and_update_dac(self, dac, value):
        """Set a voltage value on the DAC

        Args:
            dac (str): The name of the DAC to set. 'A', 'B' or 'both'
            value (float): A float between 0.0 and 5.0

        Raises:
            ValueError: On bad DAC name or bad value
        """
        to_wait = self.waittime - (time.time() - self.last_write)
        if to_wait > 0:
            time.sleep(to_wait)

        try:
            dac = self.dac_and_input_register[dac]
        except KeyError:
            message = 'Invalid dac setting \'{}\', must be on of: {}'.format(
                dac,
                list(self.dac_and_input_register.keys()),
            )
            raise ValueError(message)

        if (not isinstance(value, float)) or value < 0.0 or value > 5.0:
            message = 'Invalid value: {} Must be a float in range 0.0 -> 5.0'
            raise ValueError(message.format(value))

        # Scale by range and convert the value to 2 bytes
        relative = int(round(value / 5.0 * 65535))
        most_significant_byte = relative // 256
        least_significant_byte = relative % 256
        data = [most_significant_byte, least_significant_byte]
        self.bus.write_i2c_block_data(self.address, dac, data)

        self.last_write = time.time()

    def set_channel_A(self, voltage):  # pylint: disable=invalid-name
        """Set a voltage of channel A

        Args:
            value (float): A float between 0.0 and 5.0

        See :meth:`.write_to_and_update_dac` for details on exceptions
        """
        self.write_to_and_update_dac('A', voltage)

    def set_channel_B(self, voltage):  # pylint: disable=invalid-name
        """Set a voltage of channel B

        Args:
            value (float): A float between 0.0 and 5.0

        See :meth:`.write_to_and_update_dac` for details
        """
        self.write_to_and_update_dac('B', voltage)

    def set_both(self, voltage):
        """Set a voltage of both channels

        Args:
            value (float): A float between 0.0 and 5.0

        See :meth:`.write_to_and_update_dac` for details
        """
        self.write_to_and_update_dac('both', voltage)


def module_test():
    """Simple module test"""
    adc = AD5667()
    for number in range(100):
        adc.write_to_and_update_dac('A', number / 99.0 * 5.0)


if __name__ == '__main__':
    module_test()
