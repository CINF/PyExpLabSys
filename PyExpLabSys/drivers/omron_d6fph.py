"""Hint for implementation found at http://forum.arduino.cc/index.php?topic=285116.0 """

import smbus
import time
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class OmronD6fph(object):
    """ Class for reading pressure and temperature from Omron D6F-PH series
    Ranging not implemented for all models """

    def __init__(self):
        self.bus = smbus.SMBus(1)
        self.device_address = 0x6c
        self.full_range = 1000.0
        self.init_device()

    def init_device(self):
        """ Sensor needs to be initiated after power up """
        init_command = [0x0B, 0x00]
        self.bus.write_i2c_block_data(self.device_address, 0, init_command)

    def read_value(self, command):
        """ Read a value from the sensor """
        mcu_mode_command = [0xD0, 0x40, 0x18, 0x06]
        self.bus.write_i2c_block_data(self.device_address, 0, mcu_mode_command)
        time.sleep(0.033)
        self.bus.write_i2c_block_data(self.device_address, 0, command)
        self.bus.write_byte(self.device_address, 0x07)
        high = self.bus.read_byte(self.device_address)
        low = self.bus.read_byte(self.device_address)
        value = int(hex(high) + hex(low)[2:].zfill(2), 16)
        return value

    def read_pressure(self):
        """ Read the pressure value """
        value = self.read_value([0xD0, 0x51, 0x2C])
        #TODO: Implement range calculation for all sensor models
        pressure = (value - 1024) * self.full_range / 60000 - self.full_range/2
        return pressure

    def read_temperature(self):
        """ Read the temperature value """
        value = self.read_value([0xD0, 0x61, 0x2C])
        temperature = (value - 10214) / 37.39
        return temperature


if __name__ == '__main__':    
    OMRON = OmronD6fph()
    print(OMRON.read_pressure())
    print(OMRON.read_temperature())
