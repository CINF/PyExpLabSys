"""
Bit-banged driver for oxygen sensor. Can also work with
a proper 3.3V uart.

Notice that this sensor is highly cross-sensitive to other
gasses than oxygen.
"""
import time

import serial
import wiringpi as wp


class OCS3L(object):
    def __init__(self, gpio_pin=0, port=None):
        if port is not None:
            self.ser = serial.Serial(port, 9600, timeout=2)
            time.sleep(0.1)
        else:
            self.ser = None  # Indicates to rest of progrem to use uart
            wp.wiringPiSetup()
            self.pin = gpio_pin
            wp.pinMode(self.pin, 0)
            time.sleep(0.1)

    # Todo: This most likely does not work for the final checksum
    # calculation, that contains 9 digits
    def _checksum(self, bool_list):
        value = 0
        if len(bool_list) == 7:
            bool_list.append(0)
        for n in range(0, 8):
            value += bool_list[7 - n] * 2 ** n
            # value = value % 256
        return value

    def _uart_read(self):
        # This driver was historically written as a bit-banged driver,
        # for this reason, uart-read is now implemented to mimic the
        # output to avoid re-testing the uart-procedure.
        c = self.ser.read(self.ser.inWaiting())
        dt = 0
        while dt < 0.2:
            t = time.time()
            c = self.ser.read(1)
            dt = time.time() - t

        ret_string = [c]
        dt = 0
        while dt < 0.2:
            t = time.time()
            c = self.ser.read(1)
            dt = time.time() - t
            if dt < 0.2:
                ret_string.append(c)

        bits = []
        for char in ret_string:
            bit_string = bin(ord(char))[2:].zfill(8)
            bits.append(0)
            for bit in bit_string[::-1]:
                bits.append(int(bit))
            bits.append(0)
        return bits

    def _bitbanged_read(self):
        """
        Read the uart with bit-banged gpio, this could of course be easier
        implemented with a proper uart if one has the luxury of such a
        gadget available.
        """
        while wp.digitalRead(self.pin) == 1:
            pass

        time.sleep(0.4)

        while wp.digitalRead(self.pin) == 1:
            pass

        # Now we are certain that we have reached the signal

        raw_bits = []
        value = True
        # Todo: To optimize this, look for the second 9x0 1x1 9x0 marker.
        t = time.perf_counter()
        for i in range(0, 150):
            while wp.digitalRead(self.pin) == value:
                pass  # Keep reading until bit changes
            raw_bits.append((value, time.perf_counter() - t))
            value = not value
            if raw_bits[-1][1] > 0.1:
                break

        parsed_bytes = []

        old_bit_time = 0
        for bit in raw_bits:
            bit_time = bit[1] - old_bit_time
            old_bit_time = bit[1]
            if bit_time > 0.01:
                break

            # At 9600 baud, a bit is 104microseconds
            number_of_bytes = round((bit_time * 1e6) / 104)
            for i in range(0, number_of_bytes):
                parsed_bytes.append(1 if bit[0] else 0)

        # These bit-patterns are fixed, errors here would indicate a
        # read error in the bit-banged read.
        sanity_check = (
            parsed_bytes[8:0:-1] == [0, 0, 0, 1, 0, 1, 1, 0]
            and parsed_bytes[18:10:-1] == [0, 0, 0, 0, 1, 0, 0, 1]
            and parsed_bytes[28:20:-1] == [0, 0, 0, 0, 0, 0, 0, 1]
            and parsed_bytes[58:50:-1] == [0, 0, 0, 0, 0, 0, 0, 0]
            and
            # According to datsheet, this should be 0x63, but turns out
            # to be always 0x00
            parsed_bytes[68:60:-1] == [0, 0, 0, 0, 0, 0, 0, 0]
            and parsed_bytes[98:90:-1] == [0, 0, 0, 0, 0, 0, 0, 0]
            and parsed_bytes[108:100:-1] == [0, 0, 0, 0, 0, 0, 0, 0]
        )
        if not sanity_check:
            parsed_bytes = None
        return parsed_bytes

    def _read_oxygen(self, parsed_bytes):
        concentration_raw = parsed_bytes[38:30:-1] + parsed_bytes[48:40:-1]
        concentration = 0
        for n in range(0, 16):
            concentration += concentration_raw[15 - n] * 2 ** n
        concentration = concentration / 10.0
        return concentration

    def _read_temperature(self, parsed_bytes):
        temperature = 0
        temp_raw = parsed_bytes[78:70:-1] + parsed_bytes[88:80:-1]
        for n in range(0, 16):
            temperature += temp_raw[15 - n] * 2 ** n
        temperature = temperature / 10.0
        return temperature

    def _check_full_checksum(self, parsed_bytes):
        expected_checksum = 0
        for val in [
            0x16,
            0x09,
            0x01,
            self._checksum(parsed_bytes[38:30:-1]),
            self._checksum(parsed_bytes[48:40:-1]),
            self._checksum(parsed_bytes[78:70:-1]),
            self._checksum(parsed_bytes[88:80:-1]),
        ]:
            expected_checksum += val
            expected_checksum = expected_checksum % 256
        expected_checksum = 256 - expected_checksum

        checksum = list(reversed(parsed_bytes[110:]))

        if self._checksum(checksum[1:]) == expected_checksum:
            # This will happen for a successfull uart-read
            return True

        # Typically the bit-banged read will end here.
        filled_checksum = (9 - len(checksum)) * [1] + checksum
        success = self._checksum(filled_checksum) == expected_checksum
        return success

    def read_oxygen_and_temperature(self):
        if self.ser is None:
            parsed_bytes = self._bitbanged_read()
        else:
            parsed_bytes = self._uart_read()
        if parsed_bytes is None:
            return None

        checksum = self._check_full_checksum(parsed_bytes)
        if not checksum:
            return None

        concentration = self._read_oxygen(parsed_bytes)
        temperature = self._read_temperature(parsed_bytes)

        # msg = 'Oxygen concentration: {}%, Temperature: {}C. Checksum: {}'
        # print(msg.format(concentration, temperature, checksum))
        return (concentration, temperature)


if __name__ == '__main__':
    # oxygen_sensor = OCS3L(port='/dev/serial1')
    oxygen_sensor = OCS3L(gpio_pin=26)
    while True:
        readout = oxygen_sensor.read_oxygen_and_temperature()
        if readout is not None:
            print('Oxygen: {}%. Temperature: {}C'.format(readout[0], readout[1]))
