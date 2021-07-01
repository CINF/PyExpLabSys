""" Driver for Microchip Technology MCP3428 Analog Input device
Calibrated to PR33-13 from ncd.io other products will use different
voltage references."""
# pylint: disable=no-self-use
import time
import io
import fcntl
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class I2C:
    """ File based i2c.
    Code adapted from: https://www.raspberrypi.org/forums/viewtopic.php?t=134997"""

    def __init__(self, device, bus):
        self.file_read = io.open("/dev/i2c-"+str(bus), "rb", buffering=0)
        self.file_write = io.open("/dev/i2c-"+str(bus), "wb", buffering=0)

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
    """ Class for reading voltage from MCP3428
    For some reason this chip works only partly with smbus, hence the
    use of file based i2c.
    """

    def __init__(self):
        self.device_address = 0x68
        self.bus = I2C(self.device_address, 1)

    def __del__(self):
        self.bus.close()

    def read_sample(self, channel=1, gain=1, resolution=12):
        """ Read a single sample """
        command_byte = (self.resolution(resolution) |
                        0x00 | # One shot measuremet, use 0x10 for continous mode
                        self.gain(gain) |
                        self.channel(channel))
        self.bus.write([command_byte])

        time.sleep(0.001)

        command_byte = command_byte | 0x80 # start conversion
        self.bus.write([command_byte])

        while True:
            time.sleep(0.001)
            data = self.bus.read(3)
            if (data[2] & 0x80) == 0:
                break
        data = self.bus.read(3)
        raw_value = data[0] * 256 + data[1]
        voltage = (11.1745 * raw_value) / (2**(resolution - 1) * gain)
        return voltage

    def gain(self, gain=1):
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

    def resolution(self, resolution=12):
        """ Return the command code to set resolution """
        resolution_val = 0x00
        if resolution == 12:
            resolution_val = 0x00
        if resolution == 14:
            resolution_val = 0x04
        if resolution == 16:
            resolution_val = 0x08
        return resolution_val

    def channel(self, channel=1):
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
        return channel_val

if __name__ == '__main__':
    MCP = MCP3428()
    print(MCP.read_sample(channel=3, gain=1, resolution=16))

    #Negeativ supply should be grounded, diferential behaviour somwhat unknown
    #Calibrated to PR33-13 from ncd.io other products will use different
    #voltage references.
    #Input, Measured value
    #0.0:   0.000701904296875
    #1.0:   0.0894775390625
    #2.0:   0.178924560546875
    #3.0:   0.2685546875
    #4.0:   0.35809326171875
    #5.0:   0.447601318359375
    #6.0:   0.537109375
    #7.0:   0.626617431640625
    #8.0:   0.71612548828125
    #9.0:   0.805633544921875
    #10.0:  0.8951416015625
    #11.0:  0.984619140625
    #11.15: 0.998046875
    #11.172: Max
    #Best-fit slope: 11.1745
