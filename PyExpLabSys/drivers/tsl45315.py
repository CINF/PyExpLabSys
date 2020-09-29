""" Driver for TSL45315 Digital Ambient Light Sensor """
import os
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if on_rtd:
    pass
else:
    import smbus
import time
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


class TSL45315(object):
    """ Class for reading pressure and temperature from
    TSL45315 Digital Ambient Light Sensor """

    def __init__(self, integration_time=0):
        # Integration times:
        # 0: 400ms
        # 1: 200ms
        # 2: 100ms
        integration_times = {
            0: 0.4,
            1: 0.2,
            2: 0.1
        }
        self.integration_time = integration_times[integration_time]
        self.multiplier = 0.4 / self.integration_time
        print(self.multiplier)
        self.device_address = 0x29
        self.bus = smbus.SMBus(1)

        self.bus.write_byte_data(self.device_address, 0x80, 0x03)
        self.bus.write_byte_data(self.device_address, 0x81, integration_time)

    def read_id(self):
        value = self.bus.read_byte_data(self.device_address, 0x0A)
        print(value)

    def read_values(self):
        """ Read a value from the sensor """
        time.sleep(self.integration_time)

        data = self.bus.read_i2c_block_data(self.device_address, 0x04 | 0x80, 2)
        value = data[0] + data[1] * 255
        return self.multiplier * value


if __name__ == '__main__':
    SENSOR = TSL45315(integration_time=0)
    # print(SENSOR.read_id())
    for i in range(0, 25):
        print(SENSOR.read_values())
