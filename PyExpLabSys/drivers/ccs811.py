""" Driver for CCS811 enviromental sensor """
import smbus
import time


class CCS811(object):
    """
    Class for reading approximate values of eCO2 TVOC
    from a CC811 environmental sensor
    """
    def __init__(self):
        self.bus = smbus.SMBus(1)
        self.device_address = 0x5a
        self.status = {}
        self.status['error'] = []

        self.data = {
            'eCO2': -1,
            'TVOC': -1,
            'current': -1,
            'voltage': -1,
            'resistance': -1
        }

        if not self.verify_id():
            raise Exception('Not an CCS811!')
        self._activate()  # Todo, check for True
        self._set_drive_mode()

    def _activate(self):
        """ Take the device out of firmware update mode """
        self.bus.write_byte(self.device_address, 0xF4)
        meas_mode = self.bus.read_byte_data(self.device_address, 0x01)
        return meas_mode == 0

    def _set_drive_mode(self):
        """
        Set the sensor MEAS_MODE
        This could be done more sofisticated, but basically
        the preffered mode is always mode 1 (read once pr second)
        """
        self.bus.write_byte_data(self.device_address, 0x01, 0x00)
        time.sleep(1)
        meas_mode = self.bus.read_byte_data(self.device_address, 0x01)
        self.bus.write_byte_data(self.device_address, 0x01, 0x18)
        return None

    def hw_version(self):
        """ Read hardware version """
        hw_version = self.bus.read_byte_data(self.device_address, 0x21)
        return hex(hw_version)

    def verify_id(self):
        """ Verify that this is indeed a CCS811 """
        hw_id = self.bus.read_byte_data(self.device_address, 0x20)
        return hw_id == 0x81

    def update_status(self, status=None, error=None):
        if not status:
            status = self.bus.read_byte_data(self.device_address, 0x00)
        bit_values = bin(status)[2:].zfill(8)
        if bit_values[-8] == '1':
            self.status['Firmware mode'] = 'Application mode'
        else:
            self.status['Firmware mode'] = 'Boot mode'

        if bit_values[-5] == '1':
            self.status['Firmware status'] = 'Firmware loaded'
        else:
            self.status['Firmware mode'] = 'Firmware not loaded'

        self.status['Data ready'] = bit_values[-4] == '1'
        if bit_values[-1] == '1':
            self.read_error(error)
        else:
            self.status['error'] = []
        return self.status

    def read_error(self, error=None):
        if not error:
            error = self.bus.read_byte_data(self.device_address, 0xE0)
        bit_values = bin(error)[2:].zfill(8)
        error = []
        if bit_values[-1] == '1':
            error.append('Invalid write')
        if bit_values[-2] == '1':
            error.append('Invalid read')
        if bit_values[-3] == '1':
            error.append('Invalid MEAS_MODE')
        if bit_values[-4] == '1':
            error.append('Resistance too high, sensor not working')
        if bit_values[-5] == '1':
            error.append('Heater current error, sensor not working')
        if bit_values[-6] == '1':
            error.append('Heater voltage error, sensor not working')
        return self.status

    def update_data(self):
        """ Read data and update internal state """
        data = self.bus.read_i2c_block_data(self.device_address, 0x02, 8)
        self.data['eCO2'] = 256 * data[0] + data[1]
        self.data['TVOC'] = 256 * data[2] + data[3]

        raw_bits = bin(data[6])[2:].zfill(8) + bin(data[7])[2:].zfill(8)
        self.data['current'] = int(raw_bits[0:6], 2)
        self.data['voltage'] = int(raw_bits[6:16], 2) * 1.65 / 1023
        self.data['resistance'] = int(1000000 * self.data['voltage'] /
                                      self.data['current'])
        return self.data

    def set_environmental_data(self, humidity, temperature):
        """
        Set the environmental conditions to allow for correct
        compensation in the device
        """
        humidity_byte = ''
        for i in range(0, 16):
            bit_val = 64.0 / 2**i
            if humidity > bit_val:
                humidity_byte += '1'
                humidity -= bit_val
            else:
                humidity_byte += '0'
        hum_val = int(humidity_byte, 2)
        hum_bytes = hum_val.to_bytes(2, byteorder='big')

        temperature_byte = ''
        for i in range(0, 16):
            bit_val = 64.0 / 2**i
            if temperature + 25 > bit_val:
                temperature_byte += '1'
                temperature -= bit_val
            else:
                temperature_byte += '0'
        temperature_val = int(temperature_byte, 2)
        temp_bytes = temperature_val.to_bytes(2, byteorder='big')
        env_data = [hum_bytes[0], hum_bytes[1], temp_bytes[0], temp_bytes[1]]
        print(env_data)
        self.bus.wri2te_block_data(self.device_address, 0x05, env_data)
        time.sleep(0.5)

if __name__ == '__main__':
    sensor = CCS811()

    time.sleep(5)
    
    for i in range(0, 2000):
        time.sleep(0.1)
        status = sensor.update_status()
        print(status)
        if status['Data ready']:
            print(sensor.update_data())
        sensor.set_environmental_data(45.4, 27.3)
