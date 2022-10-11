""" Driver for Amphenol ELVH Pressure sensor """
import os
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if on_rtd:
    pass
else:
    import smbus
import time


class ELVH(object):
    """ Class for reading pressure from Amphenol ELVH """

    def __init__(self, i2cbus=1):
        self.bus = smbus.SMBus(i2cbus)
        self.device_address = 0x28

    def read(self):
        result = self.bus.read_i2c_block_data(self.device_address, 0, 4)
        temp = result[2]
        temp = temp << 8
        temp = temp | result[3]
        temp = temp >> 5
        temperature = ((temp / 10.0) - 32) * 5.0 / 9.0  # 10xF to C

        pres = result[0] & 0x3f  # Leftmost two bits are status bits, ignore
        pres = pres << 8
        pres = pres | result[1]
        pressure = pres * 68.9476 / 1000  # PSI to mbar
        return temperature, pressure


if __name__ == '__main__':
    elvh = ELVH()

    for i in range(0, 10):
        time.sleep(0.1)
        temp, pres = elvh.read()
        msg = 'Temperature: {:.1f}C. Pressure: {:.2f}mbar'
        print(msg.format(temp, pres))
