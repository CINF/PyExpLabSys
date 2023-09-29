import time
import smbus


class NXP_PCF8593(object):
    def __init__(self, i2c_address=0x51):
        self.bus = smbus.SMBus(1)
        self.device_address = i2c_address
        self.set_status()
        time.sleep(1)

    def set_status(self):
        control_and_status = self.bus.read_byte_data(self.device_address, 0x00)
        # print(control_and_status, bin(control_and_status)[2:].zfill(8))

        enable_counter = 0b00100100
        self.bus.write_byte_data(self.device_address, 0x00, enable_counter)

        alarm_status = self.bus.read_byte_data(self.device_address, 0x08)
        # print(alarm_status, bin(alarm_status)[2:].zfill(8))
        wanted_alarm = 0b00000010
        self.bus.write_byte_data(self.device_address, 0x08, enable_counter)

    def read_counter(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x01, 3)
        # print(data)
        # print(
        #     hex(data[2])[2:].zfill(2),
        #     hex(data[1])[2:].zfill(2),
        #     hex(data[0])[2:].zfill(2)
        # )
        try:
            low_digit = int(hex(data[0])[2:])
        except ValueError:
            low_digit = 0
        try:
            middle_digit = int(hex(data[1])[2:])
        except ValueError:
            middle_digit = 0
        try:
            high_digit = int(hex(data[2])[2:])
        except ValueError:
            high_digit = 0
        count = high_digit * 10 ** 4 + middle_digit * 10 ** 2 + low_digit
        return count


if __name__ == '__main__':
    pcf = NXP_PCF8593()
    time.sleep(1)

    wait_time = 2
    first_counter = pcf.read_counter()

    for i in range(0, 10):
        print()
        first_counter = pcf.read_counter()
        print('First count is: {}'.format(first_counter))
        time.sleep(wait_time)
        second_counter = pcf.read_counter()
        print('Second count is: {}'.format(second_counter))
        freq = (second_counter - first_counter) / wait_time
        print('Frequency is: {}'.format(freq))
        print('Flow if this is an FT-210: {:.3f}mL/min'.format(60 * freq / 22))
