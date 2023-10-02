import time
import smbus


class TI_ADS11x5(object):
    """
    TI11x5 analog in
    """

    def __init__(self):
        self.bus = smbus.SMBus(1)
        self.device_address = 0x49
        self.pga = {
            2 / 3: 0x0000,
            1: 0x0200,
            2: 0x0400,
            4: 0x0600,
            8: 0x0800,
            16: 0x0A00,
        }

    def read_sample(self, pga=1):
        config = 3  # Disable comperator
        data_rate = 0  # Slowest possible conversion
        config = config + self.pga[pga] + data_rate
        data0 = (config >> 8) & 0xFF
        data1 = config & 0xFF

        # Config is in register 1
        data = [data0, data1]
        self.bus.write_i2c_block_data(self.device_address, 0x01, data)

        # Value is in register 0
        time.sleep(0.3)
        data = self.bus.read_i2c_block_data(self.device_address, 0x00, 2)

        raw = 1.0 * (data[0] * 256 + data[1])
        if raw > 32767:
            raw = raw - 65535
        value = 4.096 * raw / (pga * 2 ** 15)
        return value


if __name__ == '__main__':
    ads = TI_ADS11x5()
    print(ads.read_sample(1))
