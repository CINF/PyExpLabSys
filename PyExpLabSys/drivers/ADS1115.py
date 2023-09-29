# -*- coding: utf-8 -*-

""" Driver for ADS1115 (Analog to Digital Converter) """

import smbus
import time


class ADS1115:
    def __init__(self):
        self.bus = smbus.SMBus(1)
        self.address = 0x48

        # Full-scale resolution dictionary [V]
        self.full_scale_dic = {
            '000': '6.144',
            '001': '4.096',
            '010': '2.048',
            '011': '1.024',
            '100': '0.512',
            '101': '0.256',
            '110': '0.256',
            '111': '0.256',
        }

        self.resolution_dic = {
            '6.144': 0.0001875,
            '4.096': 0.000125,
            '2.048': 0.0000625,
            '1.024': 0.00003125,
            '0.512': 0.000015625,
            '0.256': 0.0000078125,
        }

        self.internal_register_dic = {
            'Conversion': 0x00,
            'Config': 0x01,
            'Lo_thresh': 0x02,
            'Hi_thresh': 0x03,
        }

        # AINp=AIN0, AINn=AIN1, FS=+-2.048 V, 128 SPS, Continuous conversion mode
        self.init_config = [0x84, 0x83]
        self.write_config(self.init_config)
        time.sleep(0.5)

    def read_voltage(self):
        # Reads two bytes from the conversion register
        data = self.bus.read_i2c_block_data(
            self.address, self.internal_register_dic['Conversion'], 2
        )
        raw_adc = data[0] * 256 + data[1]

        if raw_adc > 32767:
            raw_adc = raw_adc - 65535

        voltage = raw_adc * self.resolution
        return voltage

    def read_config(self):
        config = self.bus.read_i2c_block_data(
            self.address, self.internal_register_dic['Config'], 2
        )
        raw_config = config[0] * 256 + config[1]
        return raw_config

    def write_config(self, command):
        if type(command) == list:
            self.config_hex = command
            self.config_binary = bin(self.config_hex[0])[2:].zfill(8) + bin(
                self.config_hex[1]
            )[2:].zfill(8)
            self.resolution = self.resolution_dic[
                self.full_scale_dic[self.config_binary[4:7]]
            ]
            self.bus.write_i2c_block_data(
                self.address, self.internal_register_dic['Config'], self.config_hex
            )
        time.sleep(0.5)

    def default_config(self):
        self.write_config([0x85, 0x83])
        time.sleep(0.5)


if __name__ == "__main__":
    adc = ADS1115()
    print(adc.read_voltage())
