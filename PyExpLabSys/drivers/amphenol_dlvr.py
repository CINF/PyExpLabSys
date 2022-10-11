""" Driver for Amphenol Digital differential og gauge sensor
This driver is disturbingly similar to Amphenol ELVH, but the
docmentation for ELVH is a lot less clear than for this.
 """
import os
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'
if on_rtd:
    pass
else:
    import smbus
import time


class AmphenolPressure(object):
    """ Class for reading pressure from Amphenol ELVH """

    def __init__(self, gauge: bool, fs: float, addr: int = 0x28, i2cbus: int = 1):
        """
        :param gauge: Indicates if this sensor measures gauge or differential
        pressure.
        :param fs: Full scale range of device in inchH20(!)
        """
        self.gauge = gauge
        if gauge:
            self.full_scale = fs
        else:
            self.full_scale = 2 * fs
        self.bus = smbus.SMBus(i2cbus)
        self.device_address = addr

    def read(self):
        result = self.bus.read_i2c_block_data(self.device_address, 0, 4)
        temp = result[2]
        temp = temp << 8
        temp = temp | result[3]
        temp = temp >> 5
        # 2047 = 2^11 - 1
        temperature = temp * (200.0/2047) - 50

        pres = result[0] & 0x3f  # Leftmost two bits are status bits, ignore
        pres = pres << 8
        pres = pres | result[1]

        if self.gauge:
            OSdig = 1638
        else:
            OSdig = 8192
        pressure = self.full_scale * 1.25 * (pres - OSdig) / 2**14
        pressure = pressure * 2.4884  # inchH20 -> mbar
        return temperature, pressure


if __name__ == '__main__':
    # This fits a DLVR-F50D-E1ND-C-NI3F
    SENSOR = AmphenolPressure(gauge=False, fs=0.5)

    for i in range(0, 10):
        print()
        time.sleep(0.1)
        temp, pres = SENSOR.read()
        msg = 'Temperature: {:.1f}C. Pressure: {:.2f}Pa'
        print(msg.format(temp, pres * 100))
