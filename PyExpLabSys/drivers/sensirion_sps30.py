"""Driver class for """
import time
import serial
import struct
import logging


class SensirionSPS30:
    """Driver for r"""

    def __init__(self, port='/dev/serial0'):
        self.serial = serial.Serial(
            port,
            baudrate=115200,
            timeout=1,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
        )

    def _calculate_checksum(self, command_bytes):
        check_sum = 0
        for char in command_bytes:
            check_sum += char

        check_sum = check_sum & 0xFF  # Only last byte is considered
        check_sum = 0xFF - check_sum
        # print('Check sum: {}'.format(hex(check_sum)))
        return check_sum

    def comm(self, command, data=[]):
        read_success = True
        length = len(data)
        first = (
            [0x7E, 0x00]  # Start  # Addr, always 0 for this device
            + [command, length]
            + data
        )
        checksum = self._calculate_checksum(first[1:])

        last = [checksum, 0x7E]  # Stop
        actual_command = first + last
        self.serial.write(actual_command)

        if not ord(self.serial.read(1)) == 0x7E:
            read_success = False
            logging.warning('First char should have been 0x7e')

        chars = bytes()
        char = self.serial.read(1)
        while not ord(char) == 0x7E:
            chars += char
            char = self.serial.read(1)

        # Reverse byte-stuffing
        chars = chars.replace(b'\x7D\x5E', b'\x7E')
        chars = chars.replace(b'\x7D\x5D', b'\x7D')
        chars = chars.replace(b'\x7D\x31', b'\x11')
        chars = chars.replace(b'\x7D\x33', b'\x13')

        if not chars[0] == 0:
            # Address, 0x7E is already stripped
            pass
        expected_checksum = self._calculate_checksum(chars[:-1])
        assert expected_checksum == chars[-1]

        state = chars[2]
        if state == 0x43:
            print('SPS30: Command {} not allowd in current state'.format(hex(command)))
        elif state > 0:
            print('SPS30: Error state: {}'.format(state))

        # Do not return header and checksum
        chars = chars[4:-1]
        return chars

    def device_info(self):
        command = 0xD0
        data = [0x00]
        product_type = self.comm(command, data)[:-1]

        data = [0x03]
        serial = self.comm(command, data)
        info = 'Product type: {}. Serial no.: {}'.format(
            product_type.decode(), serial.decode()
        )
        return info

    def clean_fan(self):
        pass

    def read_version(self):
        command = 0xD1
        data = self.comm(command)

        version = 'Firmware: {}.{}; Hardware: {}; SHDC: {}.{}'.format(
            data[0], data[1], data[3], data[5], data[6]
        )
        return version

    def device_status(self):
        """
        Check status of device, only very few errors exists, until one of them
        shows up, this is just an on/off indicator.
        """
        command = 0xD2  # Device status
        # data = [0]  # Do not clear after reading
        data = [1]  # Clear after reading
        reply = self.comm(command, data)
        status_ok = True
        for byte in reply:
            if byte > 0:
                status_ok = False
        return status_ok

    def start_measuring(self):
        command = 0x00  # Start
        data = [0x01, 0x03]  # Protocol, must be 0x01  # Big-endian IEEE754 float values
        self.comm(command, data)  # No reply from this command
        return True

    def read_measurement(self):
        command = 0x03  # Read
        # Todo, assertion error is a bit primitive, we should make
        # a dedicated exception.
        error = 0
        while -1 < error < 50:
            try:
                data = self.comm(command)
                error = -1
            except AssertionError:
                error += 1
        if error > 0:
            return None
        # Unpack 10 big-endian floats - 40 bytes in total
        parsed_data = struct.unpack(">ffffffffff", data)
        return parsed_data


if __name__ == '__main__':
    dust_sensor = SensirionSPS30()

    print(dust_sensor.device_info())
    print(dust_sensor.read_version())
    print(dust_sensor.device_status())

    dust_sensor.start_measuring()

    for i in range(0, 3):
        time.sleep(1.1)  # Todo: Read status to know if measurement is ready
        parsed_data = dust_sensor.read_measurement()
        print('MC PM1.0 [μg/m3]: {:.2f}'.format(parsed_data[0]))
        print('MC PM2.5 [μg/m3]: {:.2f}'.format(parsed_data[1]))
        print('MC PM4.0 [μg/m3]: {:.2f}'.format(parsed_data[2]))
        print('MC PM10 [μg/m3]: {:.2f}'.format(parsed_data[3]))
        print('NC NM0.5 [#/cm3]: {:.2f}'.format(parsed_data[4]))
        print('NC NM1.0 [#/cm3]: {:.2f}'.format(parsed_data[5]))
        print('NC NM2.5 [#/cm3]: {:.2f}'.format(parsed_data[6]))
        print('NC NM4.0 [#/cm3]: {:.2f}'.format(parsed_data[7]))
        print('NC NM10 [#/cm3]: {:.2f}'.format(parsed_data[8]))
        print('Typical size: [μm]: {:.2f}'.format(parsed_data[9]))
