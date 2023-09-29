# -*- coding: utf-8 -*-

""" Driver for the HTC 5500 Pro temperature controller """

import minimalmodbus
from PyExpLabSys.common.supported_versions import python3_only

python3_only(__file__)


def hex_to_dec(hex_string):
    return int(hex_string, 16)


class temperature_controller(object):
    def __init__(self, port, slave_adress=1):
        self.instrument = minimalmodbus.Instrument(port, slave_adress, mode='rtu')
        self.instrument.serial.baudrate = 9600
        self.instrument.serial.bytesize = 8
        self.instrument.serial.parity = minimalmodbus.serial.PARITY_EVEN
        self.instrument.serial.stopbits = 1
        self.instrument.serial.timeout = 1  # seconds

    def read_register(self, register):
        response = self.instrument.read_register(register)
        return response

    def write_register(self, register, setting):
        self.write_register(register, setting)

    def read_temperature(self):
        response = self.instrument.read_register(hex_to_dec('1000'), 1, signed=True)
        return response

    def read_set_temperature(self):
        response = self.instrument.read_register(hex_to_dec('1001'), 1, signed=True)
        return response

    def write_set_temperature(self, setting):
        # Resolution is 0.1 C
        self.instrument.write_register(hex_to_dec('1001'), setting, 1, signed=True)

    def read_control_method(self):
        response = self.instrument.read_register(hex_to_dec('1005'))
        return response

    def write_control_method(self, setting):
        # 0: PID, 1: ON/OFF, 2: manual tuning, 3: PID program control
        if setting == 0 or setting == 1 or setting == 2 or setting == 3:
            self.instrument.write_register(hex_to_dec('1005'), int(setting))
        else:
            print('Wrong input')
            print('0: PID, 1: ON/OFF, 2: manual tuning, 3: PID grogram control')

    def read_run_stop(self):
        response = self.instrument.read_bit(hex_to_dec('0814'))
        return response

    def write_run_stop(self, setting):
        # 0: STOP, 1: RUN (default)
        if setting == 0 or setting == 1:
            self.instrument.write_bit(hex_to_dec('0814'), int(setting))
        else:
            print('Wrong input')
            print('0: STOP, 1: RUN (default)')


if __name__ == '__main__':
    port = '/dev/ttyUSB1'

    controller = temperature_controller(port, 1)
