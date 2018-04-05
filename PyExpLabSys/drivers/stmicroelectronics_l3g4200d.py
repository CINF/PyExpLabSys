""" Driver for STMicroelectronics L3G4200D 3 axis gyroscope """
import time
import os
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if on_rtd:
    pass
else:
    import smbus
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class L3G4200D(object):
    """ Class for reading accelerometer output """

    def __init__(self):
        self.bus = smbus.SMBus(1)
        self.device_address = 0x68
        # Set output data rate to 200, bandwidth cut-off to 12.5Hz
        self.bus.write_byte_data(self.device_address, 0x20, 0x4F)
        # Set full scale range, 0x00: 250dps, 0x30: 2000dps, block until lsb and msb are read
        self.full_scale = 250 # This should go in a self-consistent table...
        self.bus.write_byte_data(self.device_address, 0x23, 0x80)
        time.sleep(0.5)

    def who_am_i(self):
        """ Device identification """
        id_byte = self.bus.read_byte_data(self.device_address, 0x0F)
        return id_byte

    def read_values(self):
        """ Read a value from the sensor """
        byte1 = self.bus.read_byte_data(self.device_address, 0x28)
        byte2 = self.bus.read_byte_data(self.device_address, 0x29)

        x_value = byte2 * 256 + byte1
        if x_value > (2**15)-1:
            x_value = x_value - 2**16
        x_value = 1.0 * x_value * self.full_scale / (2**15)

        byte1 = self.bus.read_byte_data(self.device_address, 0x2A)
        byte2 = self.bus.read_byte_data(self.device_address, 0x2B)
        y_value = byte2 * 256 + byte1
        if y_value > (2**15)-1:
            y_value = y_value - 2**16
        y_value = 1.0 * y_value * self.full_scale / (2**15)

        byte1 = self.bus.read_byte_data(self.device_address, 0x2C)
        byte2 = self.bus.read_byte_data(self.device_address, 0x2D)
        z_value = byte2 * 256 + byte1
        if z_value > (2**15)-1:
            z_value = z_value - 2**16
        z_value = 1.0 * z_value * self.full_scale / (2**15)

        return(x_value, y_value, z_value)

if __name__ == '__main__':
    L3G = L3G4200D()
    print(bin(L3G.who_am_i()))
    for i in range(0, 5):
        time.sleep(0.01)
        print(L3G.read_values())
