import time
import smbus


class MCP9808(object):
    """ Class for reading temperature from MCP9808 """

    def __init__(self, i2cbus=1):
        self.bus = smbus.SMBus(i2cbus)
        self.device_address = 0x18

    def read_values(self):
        """ Read a value from the sensor """
        self.bus.write_i2c_block_data(self.device_address, 0x01, [0x00, 0x00])

        # Set range
        self.bus.write_byte_data(self.device_address, 0x08, 0x03)
        time.sleep(1)

        data = self.bus.read_i2c_block_data(self.device_address, 0x05, 2)
        temp_temp = ((data[0] & 0x1F) * 256) + data[1]
        temp = temp_temp * 0.0625  # Scale
        return temp

    def read_resolution(self):
        res = self.bus.read_byte_data(self.device_address, 0x08)
        print(res)

    def read_manufacturer_id(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x06, 2)
        man_id = data[1]
        print('ID is: {}'.format(hex(man_id)))
        return man_id


if __name__ == '__main__':
    mcp9808 = MCP9808()
    mcp9808.read_manufacturer_id()
    mcp9808.read_resolution()
    print()
    print(mcp9808.read_values())
