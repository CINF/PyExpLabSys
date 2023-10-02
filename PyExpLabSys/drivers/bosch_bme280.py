import time
import smbus

# from ctypes import c_short
# from ctypes import c_byte
# from ctypes import c_ubyte


class BoschBME280(object):
    """
    Class for reading pressure, humidity and temperature from BoschBME280.
    Hint for implementation found at
    http://forum.arduino.cc/index.php?topic=285116.0
    """

    def __init__(self):
        self.bus = smbus.SMBus(1)
        self.device_address = 0x77
        # oversample_hum = 0b00000001 # Oversampling x 1
        # oversample_hum = 0b00000010 # Oversampling x 2
        # oversample_hum = 0b00000011 # Oversampling x 4
        # oversample_hum = 0b00000100 # Oversampling x 8
        oversample_hum = 0b00000101  # Oversampling x 16
        self.bus.write_byte_data(self.device_address, 0xF2, oversample_hum)

        # Oversample setting - same as above
        oversample_temp = 0b00000101
        oversample_pres = 0b00000101
        mode = 0b11  # Normal mode
        control = oversample_temp << 5 | oversample_pres << 2 | mode
        self.bus.write_byte_data(self.device_address, 0xF4, control)

        # 0b111: 20ms, 0b010:  125ms, 0b011: 250ms,  0b101: 1000ms
        standby = 0b111

        filter_set = 0b0  # off - 0b001: 2, 0b100: 16
        config = standby << 5 | filter_set << 2
        self.bus.write_byte_data(self.device_address, 0xF5, config)
        self._read_calibration()

    def _read_calibration(self):
        # Read blocks of calibration data from EEPROM
        # See Page 22 data sheet
        cal1 = self.bus.read_i2c_block_data(self.device_address, 0x88, 24)

        self.T = {}
        self.T['1'] = cal1[1] * 256 + cal1[0]
        # Principally these are signed, consider check
        self.T['2'] = cal1[3] * 256 + cal1[2]
        self.T['3'] = cal1[5] * 256 + cal1[4]

        self.P = {}
        self.P[1] = cal1[7] * 256 + cal1[6]
        self.P[2] = cal1[9] * 256 + cal1[8]
        self.P[3] = cal1[11] * 256 + cal1[10]
        self.P[4] = cal1[13] * 256 + cal1[12]
        self.P[5] = cal1[15] * 256 + cal1[14]
        self.P[6] = cal1[17] * 256 + cal1[16]
        self.P[7] = cal1[19] * 256 + cal1[18]
        self.P[8] = cal1[21] * 256 + cal1[20]
        self.P[9] = cal1[23] * 256 + cal1[22]

        for i in range(2, 10):
            if self.P[i] > 2 ** 15:
                self.P[i] = self.P[i] - 2 ** 16

        self.H = {}
        cal2 = self.bus.read_i2c_block_data(self.device_address, 0xA1, 1)
        self.H[1] = cal2[0]

        cal3 = self.bus.read_i2c_block_data(self.device_address, 0xE1, 7)
        self.H[2] = cal3[1] * 256 + cal3[0]
        self.H[3] = cal3[2]
        self.H[4] = cal3[3] * 16 + cal3[4] % 16
        self.H[5] = cal3[5] * 16 + (cal3[4] // 16)
        self.H[6] = cal3[6]

    def _calculate_temperature(self, temp_raw):
        var1 = (temp_raw / 16384 - self.T['1'] / 1024) * self.T['2']
        # Simplify!
        var2 = (
            ((temp_raw / 16 - self.T['1']) * (temp_raw / 16 - self.T['1']))
            / 4096
            * self.T['3']
            / 2 ** 14
        )

        t_fine = var1 + var2
        # Which is correct?!?
        temperature = t_fine / 5120
        # temperature = (( t_fine * 5) + 128) / 256
        # temperature = temperature / 100.0
        return temperature, t_fine

    def _calculate_pressure(self, pres_raw, t_fine):
        v1 = t_fine / 2.0 - 64000.0
        v2 = (((v1 / 4.0) * (v1 / 4.0)) / 2048) * self.P[6]
        v2 += (v1 * self.P[5]) * 2.0
        v2 = (v2 / 4.0) + (self.P[4] * 65536.0)
        v1 = (
            ((self.P[3] * (((v1 / 4.0) * (v1 / 4.0)) / 8192)) / 8)
            + ((self.P[2] * v1) / 2.0)
        ) / 262144
        v1 = ((32768 + v1) * self.P[1]) / 32768

        if v1 == 0:
            return 0

        pressure = ((1048576 - pres_raw) - (v2 / 4096)) * 3125
        if pressure < 0x80000000:
            pressure = (pressure * 2.0) / v1
        else:
            pressure = (pressure / v1) * 2

        v1 = (self.P[9] * (((pressure / 8.0) * (pressure / 8.0)) / 8192.0)) / 4096
        v2 = ((pressure / 4.0) * self.P[8]) / 8192.0
        pressure = pressure + ((v1 + v2 + self.P[7]) / 16.0)
        return pressure / 100

    def _calculate_humidity(self, hum_raw, t_fine):
        humidity = t_fine - 76800.0
        humidity = (hum_raw - (self.H[4] * 64.0 + self.H[5] / 2 ** 14 * humidity)) * (
            self.H[2]
            / 2 ** 16
            * (
                1.0
                + self.H[6]
                / 2 ** 26
                * humidity
                * (1.0 + self.H[3] / 2 ** 26 * humidity)
            )
        )
        humidity = humidity * (1.0 - self.H[1] * humidity / 2 ** 19)
        if humidity > 100:
            humidity = 100
        elif humidity < 0:
            humidity = 0
        return humidity

    def _read_ids(self):
        (nr, version) = self.bus.read_i2c_block_data(self.device_address, 0xD0, 2)
        # time.sleep(0.1)
        return {'id_number:': nr, 'version': version}

    def measuring(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0xF3, 1)
        measure_bit = data[0] >> 3
        return measure_bit

    def read_all_values(self):
        while not self.measuring():
            time.sleep(0.01)
        while self.measuring():
            time.sleep(0.01)

        data = self.bus.read_i2c_block_data(self.device_address, 0xF7, 8)
        pres_raw = data[0] * 4096 + data[1] * 16 + data[2] // 16
        temp_raw = data[3] * 4096 + data[4] * 16 + data[5] // 16
        hum_raw = data[6] * 256 + data[7]

        temperature, t_fine = self._calculate_temperature(temp_raw)
        air_pressure = self._calculate_pressure(pres_raw, t_fine)
        humidity = self._calculate_humidity(hum_raw, t_fine)

        return_dict = {
            'temperature': temperature,
            'humidity': humidity,
            'air_pressure': air_pressure,
        }
        return return_dict


if __name__ == '__main__':
    BOSCH = BoschBME280()

    t = time.time()
    iterations = 20
    for i in range(0, iterations):
        values = BOSCH.read_all_values()
        msg = 'Temperature: {:.2f}C, Pressure: {:.2f}Pa, Humidity: {:.2f}%'
        print(
            msg.format(
                values['temperature'], values['air_pressure'], values['humidity']
            )
        )
    print('Time pr iteration: {:.3f}s'.format((time.time() - t) / iterations))
