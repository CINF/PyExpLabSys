"""Driver for the EL-USB-RT temperature and humidity USB device from Lascar

Calling read on the device will return either the temperature or the
humidity.

If the first byte is \x03 it is a temperature. The next 2 bytes is a unsigned
integer which, is used to calculate the temperature as:

    temp = -100 * 0.1 * (unsigned_short)

If the first byte is \x02 it is humidity. The next byte is an unsigned char,
which is used to calculate the relative humidity as:

    humidity = 0.5 * (unsigned_char)

"""

from __future__ import division, print_function

import struct
try:
    import hid
except (ImportError, AttributeError):
    print("Cannot import hid, can be install with pip")
except SyntaxError:
    print("This module makes use of hid, which is only available for Python2")


class ElUsbRt(object):
    """Driver for the EL-USB-RT device"""

    def __init__(self, device_path=None):
        if device_path is None:
            for dev in hid.enumerate():
                if dev['product_string'] == 'EL USB RT':
                    path = dev['path']

        if path is None:
            message = 'No path give and unable to find it'
            raise ValueError(message)

        self.dev = hid.Device(path=path)

    def get_temperature_and_humidity(self):
        """Returns the temperature (in celcius, float) and relative humidity
        (in %, float) in a dict

        """
        out = {}
        while len(out) < 2:
            string = self.dev.read(8)
            if string.startswith('\x03'):
                frac, = struct.unpack('H', string[1:])
                out['temperature'] = -200 + frac * 0.1
            elif string.startswith('\x02'):
                frac, = struct.unpack('B', string[1:])
                out['humidity'] = frac * 0.5
        return out

    def get_temperature(self):
        """Returns the temperature  (in celcius, float)"""
        while True:
            string = self.dev.read(8)
            if string.startswith('\x03'):
                frac, = struct.unpack('H', string[1:])
                return -200 + frac * 0.1


if __name__ == '__main__':
    DEV = ElUsbRt()
    while True:
        print(DEV.get_temperature())
