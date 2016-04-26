""" Driver for HIH6000 class temperature and humidity sensors """
import os
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if on_rtd:
    pass
else:
    import smbus
import time
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class HIH6130(object):
    """ Class for reading pressure and temperature from
    Honeywell HumidIcon HIH-6130/6131 """

    def __init__(self):
        self.bus = smbus.SMBus(1)
        self.device_address = 0x27

    def read_values(self):
        """ Read a value from the sensor """
        self.bus.write_quick(0x27)
        time.sleep(0.05)
        result = self.bus.read_i2c_block_data(self.device_address, 0, 4)

        # Two upper bits of byte 0 are stauts bits
        status = (result[0] & 0b11000000) >> 6
        if status > 1: # Error
            return None

        # The rest of byte 0 is the most significant byte of the total 14 bit value
        hum_high = (result[0] & 0b111111) << 8
        # Add this to lower byte to fill in the lower 8 bit
        hum_total = hum_high + result[1]
        hum_calibrated = hum_total * 100.0 / (2**14 - 1)
        
        #3rd byte contans the upper 8 bits of temperature, make room to the six lower bits
        temp_high = result[2] << 6
        #4th byte contains the lower six bits, shifted by two empty bits
        temp_low = + (result[3] & 0b11111100) >> 2
        temp = temp_high + temp_low
        temp_calibrated = (temp * 165.0 / (2**14-1)) - 40
        return(hum_calibrated, temp_calibrated)


if __name__ == '__main__':
    HIH = HIH6130()
    print(HIH.read_values())
