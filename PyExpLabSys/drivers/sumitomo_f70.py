import serial

from icecream import ic


class SumitomoF70(object):
    def __init__(self, port='/dev/ttyUSB0'):
        # Default comm parameters are correct, we could choose to set them though
        self.serial = serial.Serial(port)
        print(self.serial)
        self.serial.timeout = 0.2

    @staticmethod
    def _crc(command):
        # Adapted from https://github.com/Kalebu/crc16-modbus-in-Python
        xor_value = 0xA001
        crc = 0xFFFF
        for byte in command:
            crc = crc ^ ord(byte)
            for _ in range(8):
                if (crc & 1):  # LSB is 1
                    crc = crc >> 1
                    crc = crc ^ xor_value
                else:
                    crc = crc >> 1

        return_val = hex(crc)[2:].upper()
        return return_val

    def _read_from_device(self, command, debug=False):
        comm = command + self._crc(command) + '\r'
        comm = comm.encode('ascii')
        self.serial.write(comm)
        reply = ''
        next_char = reply = self.serial.read(1)
        while len(next_char) > 0:
            next_char = self.serial.read(1)
            reply = reply + next_char

        expected_crc = int(self._crc(reply[:-5].decode()), 16)
        try:
            actual_crc = int(reply[-5:-1].decode(), 16)
        except ValueError:
            print('Cannot read crc from string {}'.format(reply))
            actual_crc = ''

        # ic(expected_crc, actual_crc)
        if expected_crc == actual_crc:
            pre_cut = len(command) + 1  # Original command + comma
            post_cut = -6  #  comma, 4 crc digits, CR
            return_val = reply[pre_cut:post_cut].decode()
        else:
            return_val = None
        return return_val

    def _comm(self, command):
        error = 0
        while error > -1 and error < 10:
            return_val = self._read_from_device(command)
            if return_val is None:
                error = error + 1
                if error > 2:
                    ic('Error is {}'.format(error))
            else:
                error = -1
        return return_val

    def read_firmware_and_run_hours(self):
        command = '$ID1'
        reply_raw = self._comm(command)
        print(reply_raw)
        return reply_raw

    def read_temperature(self):
        command = '$TEA'
        reply_raw = self._comm(command)
        temperatures_raw = reply_raw.split(',')
        temperatures = {
            'discharge_temp': float(temperatures_raw[0]),
            'water_outlet_temp': float(temperatures_raw[1]),
            'water_inlet_temp': float(temperatures_raw[2]),
        }
        return temperatures

    def read_pressure(self):
        command = '$PRA'
        reply_raw = self._comm(command)
        # print(reply_raw)
        pressure = float(reply_raw.split(',')[0])
        pressure_in_bar = pressure * 0.0689476
        return pressure_in_bar

    def read_status(self):
        command = '$STA'
        raw_reply = self._comm(command)
        print(raw_reply)
        # raw_reply = '0301'
        msb = int(raw_reply[0:2], 16)
        lsb = int(raw_reply[2:4], 16)

        system_on =           bool(lsb & 0b00000001)
        motor_alam =          bool(lsb & 0b00000010)
        phase_sequence_alam = bool(lsb & 0b00000100)
        helium_temp_alam =    bool(lsb & 0b00001000)
        water_temp_alam =     bool(lsb & 0b00010000)
        water_flow_alam =     bool(lsb & 0b00100000)
        oil_level_alam =      bool(lsb & 0b01000000)
        pressure_alam =       bool(lsb & 0b10000000)
        solenoid_on =         bool(msb & 0b00000001)

        state_lsb =           msb & 0b00000010
        state_center =        msb & 0b00000100
        state_msb =           msb & 0b00001000
        state = 0b111 & (msb >> 1)

        configureation_bit =  msb & 0b10000000

        print(state_lsb, state_center, state_msb)
        # Known value: Off is 000

        status = {
            'system_on': system_on,
        }
        return status


if __name__ == '__main__':
    F70 = SumitomoF70('/dev/ttyUSB1')

    # Command to turn on compressor - not currently
    # implemented in main driver
    # cmd = b'$ON177CF\r'
    # F70.serial.write(cmd)

    print('temperature')
    print(F70.read_temperature())
    print()
    print('pressure')
    print(F70.read_pressure())
    print()
    print('status')
    print(F70.read_status())

    print('Firmware and run hours')
    print(F70.read_firmware_and_run_hours())
