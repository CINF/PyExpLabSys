""" Driver for Microchip Technology MCP3428 Analog Input device
Calibrated to PR33-13 from ncd.io other products will use different
voltage references."""
# pylint: disable=no-self-use
import time
import io
import fcntl


class I2C:
    """File based i2c.
    Code adapted from: https://www.raspberrypi.org/forums/viewtopic.php?t=134997"""

    def __init__(self, device, bus):
        self.file_read = io.open("/dev/i2c-" + str(bus), "rb", buffering=0)
        self.file_write = io.open("/dev/i2c-" + str(bus), "wb", buffering=0)

        i2c_slave = 0x0703
        # set device address
        fcntl.ioctl(self.file_read, i2c_slave, device)
        fcntl.ioctl(self.file_write, i2c_slave, device)

    def write(self, values):
        """ Write a value to i2c port """
        self.file_write.write(bytearray(values))

    def read(self, number_of_bytes):
        """ Read value from i2c port"""
        value_bytes = self.file_read.read(number_of_bytes)
        return list(value_bytes)

    def close(self):
        """ Close the device """
        self.file_write.close()
        self.file_read.close()


class MCP3428(object):
    """Class for reading voltage from MCP3428
    For some reason this chip works only partly with smbus, hence the
    use of file based i2c.
    """

    def __init__(self, address_index=0, voltage_ref=2.048):
        self.voltage_ref = voltage_ref  # On ncd.io devices, this is approx ~11.1745V
        self.device_address = 0x68 + address_index
        self.bus = I2C(self.device_address, 1)

    def __del__(self):
        self.bus.close()

    def read_sample(
        self, channel: int = 1, gain: int = 1, resolution: int = 12
    ) -> float:
        """ Read a single sample """
        command_byte = (
            self.resolution(resolution)
            | 0x00
            | self.gain(gain)  # One shot measuremet, use 0x10 for continous mode
            | self.channel(channel)
        )
        command_byte = command_byte | 0x80  # start conversion
        self.bus.write([command_byte])

        # t = time.time()
        while True:
            time.sleep(0.001)
            data = self.bus.read(3)
            if (data[2] & 0x80) == 0:
                break
        # meas_time = time.time() - t
        # print('High: {}, Low: {}'.format(
        # bin(data[0])[2:].zfill(8), bin(data[1])[2:].zfill(8)))
        # print('Execution time: {:.2f}ms'.format(meas_time * 1000))

        raw_value = data[0] * 256 + data[1]
        if raw_value > (2 ** (resolution - 1) - 1):
            raw_value = raw_value - 2 ** resolution
        # print('Raw sensor value: {}'.format(raw_value))
        bit_size = self.voltage_ref / (2 ** (resolution - 1) * gain)
        voltage = raw_value * bit_size
        return voltage

    def gain(self, gain: int = 1) -> int:
        """ Return the command code to set gain """
        gain_val = 0x00
        if gain == 1:
            gain_val = 0x00
        if gain == 2:
            gain_val = 0x01
        if gain == 4:
            gain_val = 0x02
        if gain == 8:
            gain_val = 0x03
        return gain_val

    def resolution(self, resolution: int = 12) -> int:
        """ Return the command code to set resolution """
        resolution_val = 0x00
        if resolution == 12:
            resolution_val = 0x00
        if resolution == 14:
            resolution_val = 0x04
        if resolution == 16:
            resolution_val = 0x08
        return resolution_val

    def channel(self, channel: int = 1) -> int:
        """ Return the command code to set channel """
        channel_val = 0x00
        if channel == 1:
            channel_val = 0x00
        if channel == 2:
            channel_val = 0x20
        if channel == 3:
            channel_val = 0x40
        if channel == 4:
            channel_val = 0x60
        # print('Channel val: {}, bin: {}'.format(channel_val, bin(channel_val)))
        return channel_val


if __name__ == '__main__':
    MCP = MCP3428(address_index=4)
    print(MCP.read_sample(channel=1, gain=1, resolution=16) * (3.3 + 2.2) / 2.2)
    print(MCP.read_sample(channel=2, gain=1, resolution=16) * (3.3 + 2.2) / 2.2)
    print(MCP.read_sample(channel=3, gain=1, resolution=16) * (3.3 + 2.2) / 2.2)
    print(MCP.read_sample(channel=4, gain=1, resolution=16) * (3.3 + 2.2) / 2.2)
    print()

    # for adc_index in range(0, 8):
    #     adc = MCP3428(adc_index)
    #     values = []
    #     for channel in range(0, 4):
    #         values.append(adc.read_sample(channel=channel, gain=1, resolution=16))
    #     print('ADC: {}: {}'.format(adc_index, values))
