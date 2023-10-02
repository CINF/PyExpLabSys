import smbus
import time


class AsairAht20(object):
    """Class for reading pressure and temperature from Omron D6F-PH series
    Ranging not implemented for all models"""

    def __init__(self):
        self.bus = smbus.SMBus(1)
        self.device_address = 0x38
        self.init_device()

    def _read_status(self):
        self.bus.write_byte(self.device_address, 0x71)
        response = self.bus.read_byte(self.device_address)
        # print('Status: {}, bin: {}'.format(response, bin(response)))
        return response

    def init_device(self):
        """ Sensor needs to be initiated after power up """
        # Reset sensor:
        self.bus.write_byte(self.device_address, 0xBA)
        time.sleep(0.03)

        # Calibrate sensor:
        init_command = [0x08, 0x00]
        self.bus.write_i2c_block_data(self.device_address, 0xBE, init_command)

        calibrated = False
        while not calibrated:
            response = self._read_status()
            calibrated = response & 0b1000
        time.sleep(0.2)
        # Device is now calibrated and ready for operation
        return True

    def read_value(self):
        """ Read a value from the sensor """
        read_command = [0x33, 0x00]
        self.bus.write_i2c_block_data(self.device_address, 0xAC, read_command)
        time.sleep(0.1)
        value = self.bus.read_i2c_block_data(self.device_address, 0x00, 6)
        # msg = 'State: {}, hex: {}, bin: {}'
        # print(msg.format(value[0], hex(value[0]), bin(value[0])))
        # print('Humidity: {} {}'.format(value[1], value[2]))
        # print('Shared byte: {}'.format(value[3]))
        # print('Temperature: {}'.format(value[4] + value[5]))
        humidity_high = value[1] << 12
        humidity_mid = value[2] << 4
        humidity_low = value[3] >> 4
        humidity = humidity_high + humidity_mid + humidity_low
        humidity_cal = 100.0 * humidity / 2 ** 20

        temp_high = (value[3] & 0b00001111) << 16
        temp_mid = value[4] << 8
        temp_low = value[5]
        temperature = temp_high + temp_mid + temp_low
        temperature_cal = 200.0 * temperature / 2 ** 20 - 50
        return humidity_cal, temperature_cal


if __name__ == '__main__':
    ASAIR = AsairAht20()
    humidity, temperature = ASAIR.read_value()
    print('Temperature: {:.2f}C, Humidity: {:.2f}%'.format(temperature, humidity))
