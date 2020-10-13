import smbus


class XP_PS(object):
    def __init__(self):
        self.bus = smbus.SMBus(1)
        self.device_address = 0x51

    def read_manufacturer(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x00, 16)
        return_string = ''
        for char in data:
            return_string += chr(char)
        return_string = return_string.strip()
        return return_string

    def read_model(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x10, 16)
        return_string = ''
        for char in data:
            return_string += chr(char)
        return_string = return_string.strip()
        return return_string

    def read_serial_nr(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x30, 16)
        return_string = ''
        for char in data:
            return_string += chr(char)
        return_string = return_string.strip()
        return return_string

    def read_temperature(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x68, 1)
        value = int(str(data[0]), 16)
        return value

    def read_status(self):
        print()
        print('Status 0x6c:')
        error1 = self.bus.read_i2c_block_data(self.device_address, 0x6c, 1)
        error_bits = bin(error1[0])[2:].zfill(8)
        if error_bits[7] == '1':
            print('OVP Shutdown')
        if error_bits[6] == '1':
            print('OLP Shutdown')
        if error_bits[5] == '1':
            print('OTP Shutdown')
        if error_bits[4] == '1':
            print('Fan Failure')
        if error_bits[3] == '1':
            print('AUX og SMPS Fail')
        if error_bits[2] == '1':
            print('HI-Temp')
        if error_bits[1] == '1':
            print('AC power de-rating')
        if error_bits[0] == '1':
            print('AC Input Failure')

        print()
        print('Status 0x6f:')
        error2 = self.bus.read_i2c_block_data(self.device_address, 0x6f, 1)
        error_bits = bin(error2[0])[2:].zfill(8)
        if error_bits[7] == '1':
            print('Inhibit by VCI / ACI or ENB')
        if error_bits[6] == '1':
            print('CMD Active')
        assert (error_bits[5] == '0')
        assert (error_bits[4] == '0')
        if error_bits[3] == '1':
            print('Status on')
        assert (error_bits[2] == '0')
        assert (error_bits[1] == '0')
        if error_bits[0] == '1':
            print('Remote on')

        print()
        print('Control:')
        control = self.bus.read_i2c_block_data(self.device_address, 0x7c, 1)
        error_bits = bin(control[0])[2:].zfill(8)
        # print('Control bits: {}'.format(error_bits))
        if error_bits[7] == '1':
            print('Power On')
        if error_bits[5] == '1':
            print('Command required')
        if error_bits[4] == '1':
            print('Command error')
        assert (error_bits[3] == '0')
        assert (error_bits[2] == '0')
        # Bit 1 is reserved, cannot predict what happens
        if error_bits[0] == '1':
            print('Control by i2c')
        print()

    def read_max_values(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x50, 2)
        print((256*data[1] + data[0]) / 100.0)
        data = self.bus.read_i2c_block_data(self.device_address, 0x52, 2)
        print((256*data[1] + data[0]) / 100.0)
        data = self.bus.read_i2c_block_data(self.device_address, 0x56, 2)
        print((256*data[1] + data[0]) / 100.0)
        data = self.bus.read_i2c_block_data(self.device_address, 0x54, 2)
        print((256*data[1] + data[0]) / 100.0)

    def read_actual_values(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x60, 2)
        print('Voltage: {}V'.format((256*data[1] + data[0]) / 100.0))
        data = self.bus.read_i2c_block_data(self.device_address, 0x62, 2)
        print('Current: {}A'.format((256*data[1] + data[0]) / 100.0))

    def remote_enable(self):
        control = 2**7 + 1
        # control = 1
        self.bus.write_i2c_block_data(self.device_address, 0x7c, [control])

    def set_voltage(self, voltage):
        # Todo, check value is within range
        decivoltage = int(voltage * 100)
        high_byte = decivoltage >> 8
        low_byte = decivoltage % 256

        data = [low_byte, high_byte]
        print('Voltage data: {}'.format(data))
        self.bus.write_i2c_block_data(self.device_address, 0x70, data)
        # Execute change (0x84 to abondon):
        self.bus.write_i2c_block_data(self.device_address, 0x7c, [0x85])

    def set_current(self, current):
        # Todo, check value is within range
        decicurrent = int(current * 100)
        high_byte = decicurrent >> 8
        low_byte = decicurrent % 256
        data = [low_byte, high_byte]
        print('Current data: {}'.format(data))
        self.bus.write_i2c_block_data(self.device_address, 0x72, data)
        # Execute change (0x84 to abondon):
        self.bus.write_i2c_block_data(self.device_address, 0x7c, [0x85])


if __name__ == '__main__':
    xp = XP_PS()
    # xp.remote_enable()

    # time.sleep(1)

    # xp.set_voltage(1.11)
    # xp.set_current(1.0)

    # xp.read_status()
    # exit()

    # print('Manufacturer: {}'.format(xp.read_manufacturer()))
    # print('Model: {}'.format(xp.read_model()))
    # print('Serial: {}'.format(xp.read_serial_nr()))
    # print('Temperature: {}C'.format(xp.read_temperature()))
    # print()
    # print(xp.read_max_values())
    # print()
    print(xp.read_actual_values())
