""" Driver for AIS328DQTR 3 axis accelerometer """
import time
import os
from PyExpLabSys.common.supported_versions import python2_and_3
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
python2_and_3(__file__)
if on_rtd:
    pass
else:
    import smbus

class MMA7660FC(object):
    """ Class for reading accelerometer output """

    def __init__(self):
        self.bus = smbus.SMBus(1)
        self.device_address = 0x4c
        # Turn on the device through MODE register (7)
        self.bus.write_byte_data(self.device_address, 0x07, 0x01)
        # Number of samples pr seconds, registor 8
        self.bus.write_byte_data(self.device_address, 0x08, 0x07)

        time.sleep(0.5)

    def read_values(self):
        """ Read a value from the sensor """

        data = self.bus.read_i2c_block_data(0x4C, 0x00, 5)
        x_value = data[0] & 0x3F
        if x_value > 31:
            x_value = x_value - 64
        x_value = x_value * 1.5 / 32

        y_value = data[1] & 0x3F
        if y_value > 31:
            y_value = y_value - 64
        y_value = y_value * 1.5 / 32

        z_value = data[2] & 0x3F
        if z_value > 31:
            z_value = z_value - 64
        z_value = z_value * 1.5 / 32

        return(x_value, y_value, z_value)

if __name__ == '__main__':
    MMA = MMA7660FC()
    for i in range(0, 20):
        time.sleep(0.05)
        print(MMA.read_values())
