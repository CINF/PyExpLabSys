import time
import smbus


class NXP_PCF8593(object):
    def __init__(self, i2c_address=0x51):
        self.bus = smbus.SMBus(1)
        # self.bus.pec = True  # Enable PEC-check, is this good?
        self.device_address = i2c_address

    def read_status(self):
        control_and_status = self.bus.read_byte_data(self.device_address, 0x00)
        print(control_and_status, bin(control_and_status)[2:].zfill(8))
        enable_counter = 0b00100100
        # enable_counter = 0b00000000
        self.bus.write_byte_data(self.device_address, 0x00, enable_counter)

        alarm_status = self.bus.read_byte_data(self.device_address, 0x08)
        print(alarm_status, bin(alarm_status)[2:].zfill(8))
        wanted_alarm = 0b00000010
        self.bus.write_byte_data(self.device_address, 0x08, enable_counter)
        
    def read_counter(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x01, 3)
        # # print(data)
        # for i in range(0, 3):
        #     print('Byte {}h: {}'.format(str((i + 1)).zfill(2), hex(data[i])))
        value_str = ''
        for i in range(0, 3):
            value_str += hex(data[2 - i])[2:].zfill(2)
        value = int(value_str)
        return value

if __name__ == '__main__':
    pcf = NXP_PCF8593()

    print('Status')
    pcf.read_status()

    # print()
    # pcf.read_counter()

    print('Counter')
    for i in range(0, 1):
        print(pcf.read_counter())
