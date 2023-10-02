import time
import smbus


class XP_HPA_PS(object):
    def __init__(self, i2c_address=0x5F):
        self.bus = smbus.SMBus(1)
        self.bus.pec = True  # Enable PEC-check, is this good?
        self.device_address = i2c_address

    def read_manufacturer(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x99, 16)
        return_string = ''
        for char in data:
            return_string += chr(char)
        return_string = return_string.strip()
        return return_string

    def read_model(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x9A, 32)
        return_string = ''
        for char in data:
            return_string += chr(char)
        return_string = return_string.strip()
        return return_string

    def read_serial_nr(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x9E, 16)
        return_string = ''
        for char in data:
            return_string += chr(char)
        return_string = return_string.strip()
        return return_string

    def read_temperatures(self, read_all=True):
        """
        Returned as a tuple of both sensors (sensor1, sensor2).
        Remember that sensor 2 is considered primary!
        """
        temperature1 = 0
        if read_all:
            # Temperature sensor 1 - secondary
            data = self.bus.read_i2c_block_data(self.device_address, 0x8D, 2)
            temperature1 = 256 * data[1] + data[0]

        # Temperature sensor 2 - primary
        data = self.bus.read_i2c_block_data(self.device_address, 0x8E, 2)
        temperature2 = 256 * data[1] + data[0]
        return (temperature1, temperature2)

    def read_temperature(self):
        """
        Read just the primary sensor
        """
        _, temp = self.read_temperatures(read_all=False)
        return temp

    def _decode_linear(self, data):
        exp = data[1] >> 3
        high_mantissa = (data[1] & 0b00000111) << 8
        mantissa = data[0] + high_mantissa
        if exp > 16:
            exp = exp - 2 ** 5
        value = 1.0 * mantissa * 2 ** exp
        return value

    def read_fan_speeds(self):
        speeds = []
        for i in range(0, 4):
            data = self.bus.read_i2c_block_data(self.device_address, 0x90 + i, 2)
            speed = self._decode_linear(data)
            speeds.append(speed)
        return speeds

    def read_input_voltage(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x55, 2)
        fault_limit = self._decode_linear(data)
        data = self.bus.read_i2c_block_data(self.device_address, 0x88, 2)
        v_in = self._decode_linear(data)
        return_value = {'fault_limit': fault_limit, 'v_in': v_in}
        return return_value

    def read_actual_voltage(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x8B, 2)
        # print('Actual voltage readback: {}'.format(data))
        voltage = (256 * data[1] + data[0]) / 1024.0
        return voltage

    def read_actual_current(self):
        data = self.bus.read_i2c_block_data(self.device_address, 0x8C, 2)
        current = self._decode_linear(data)
        return current

    # Full combined status read 0x79

    def _common_status_read(self, address, error_list):
        # Currently only works for 1-byte lists, for an example of a two-byte
        # list, see read_user_configuration()
        actual_errors = []
        data = self.bus.read_i2c_block_data(self.device_address, address, 1)
        bits = bin(data[0])[2:].zfill(8)
        length = len(error_list)
        for i in range(0, length):
            if bits[length - 1 - i] == '1':
                actual_errors.append(error_list[i])
        return actual_errors

    def read_status_byte(self):
        """
        Fast combined status read, will give a rough overview.
        """
        error_values = [
            'NONE_OF_THE_ABOVE',
            'CML',
            'TEMPERATURE',
            'VIN_UV_FAULT',
            'IOUT_OC_FAULT',
            'VOUT_OV_FAULT',
            'OFF',
            'BUSY',
        ]
        actual_errors = self._common_status_read(0x78, error_values)
        return actual_errors

    def read_voltage_out_status(self):
        error_values = [
            'Not used',
            'Not used',
            'Not used',
            'Not used',
            'VOUT_UV_FAULT',
            'VOUT_UV_WARNING',
            'VOUT_OV_WARNING',
            'VOUT_OV_FAULT',
        ]
        actual_errors = self._common_status_read(0x7A, error_values)
        return actual_errors

    def read_current_out_status(self):
        error_values = [
            'Not used',
            'Not used',
            'IN_POWER_LIMIT',
            'Not used',
            'Not used',
            'IOUT_OC_WARNING',
            'IOUT_OC_LV_FAULT',
            'OUT_OC_FAULT',
        ]
        actual_errors = self._common_status_read(0x7B, error_values)
        return actual_errors

    def read_ac_input_status(self):
        error_values = [
            'Not used',
            'Not used',
            'Not used',
            'Not used',
            'VIN_UV_FAULT',
            'VIN_UV_WARNING',
            'VIN_OV_WARNING',
            'VIN_OV_FAULT',
        ]
        actual_errors = self._common_status_read(0x7C, error_values)
        return actual_errors

    def read_temperature_status(self):
        error_values = [
            'OT_PRELOAD',
            'Not used',
            'Not used',
            'Not used',
            'Not used',
            'Not used',
            'OT_WARNING',
            'OT_FAULT',
        ]
        actual_errors = self._common_status_read(0x7D, error_values)
        return actual_errors

    def read_communication_status(self):
        error_values = [
            'MEM_LOGIC_FAULT',
            'OTHER_CML_FAULT',
            'Reserved - Not used',
            'MCU_FAULT',
            'MEMORY_FAULT',
            'PEC_FAILED',
            'INVALID_DATA',
            'INVALID_COMMAND',
        ]
        actual_errors = self._common_status_read(0x7E, error_values)
        return actual_errors

    # 0x81 Fans 1 and 2
    # 0x82 Fans 3 and 4

    def read_user_configuration(self):
        values = [
            'CFG_CURRENT_SOFTSTART_ENABLE',
            'CFG_FAST_SOFTSTART_DISABLE',
            'CFG_PRELOAD_DISABLE',
            'CFG_FAN_OFF',
            'CFG_ACOK_SIG_LOGIC',
            'CFG_DCOK_SIG_LOGIC',
            'Reserved',
            'CFG_FAN_TEMP_OK_SIG_LOGIC',
            'CFG_SYNC_PWR_ON',
            'CFG_REMOTE_INHIBIT_LOGIC',
            'CFG_POTENTIOMETER_DISABLE',
            'CFG_POTENTIOMETER_FULL_ADJ',
            'CFG_ANALOG_PROG',
            'CFG_DISABLE_IPROG',
            'CFG_DISABLE_VPROG',
            'CFG_NO_PRELOAD_IN_SD',
        ]
        # Consider to extend _common_status_read() to handle this
        actual_settings = []
        data = self.bus.read_i2c_block_data(self.device_address, 0xD6, 2)
        data_sum = data[1] * 256 + data[0]
        bits = bin(data_sum)[2:].zfill(16)
        for i in range(0, 16):
            if bits[16 - 1 - i] == '1':
                actual_settings.append(values[i])
        return actual_settings

    @staticmethod
    def _set_bit(index, bits, wanted_state):
        current_state = (bits >> index) & 1
        if current_state == 1:
            bits = bits - 2 ** index
        # Wanted bit is now clear, set it according to wish
        if wanted_state:
            bits += 2 ** index
        return bits

    def configure_user_settings(self, cfg_fan_off=None, cfg_remote_inhibit_logic=None):
        # Read current state
        data = self.bus.read_i2c_block_data(self.device_address, 0xD6, 2)
        data_sum = data[1] * 256 + data[0]

        if cfg_fan_off is not None:
            data_sum = self._set_bit(3, data_sum, cfg_fan_off)
        if cfg_remote_inhibit_logic is not None:
            data_sum = self._set_bit(9, data_sum, cfg_remote_inhibit_logic)

        # Write back new state
        high_byte = data_sum >> 8
        low_byte = data_sum % 256
        data = [low_byte, high_byte]
        self.bus.write_i2c_block_data(self.device_address, 0xD6, data)

    def operation(self, turn_on=False, turn_off=False):
        """
        Turn on or off the DC output
        """
        if turn_on == turn_off:
            value = None
        elif turn_on:
            value = [0x80]
        elif turn_off:
            value = [0x00]

        if value is not None:
            self.bus.write_i2c_block_data(self.device_address, 0x01, value)
        time.sleep(0.05)
        data = self.bus.read_i2c_block_data(self.device_address, 0x01, 1)
        # print('Operation value: {}'.format(data))
        # Should be 0, since this is what we just send
        return data[0]

    def clear_errors(self):
        self.bus.write_byte(self.device_address, 0x03)
        time.sleep(0.05)
        return True

    def store_user_all(self):
        """
        Write current settings to non-volatile memory as new defaults
        """
        self.bus.write_byte(self.device_address, 0x15)
        time.sleep(0.05)
        return True

    def write_enable(self):
        """
        Device starts in write-protected mode, this needs to be called
        before it is possible to change any values.
        """
        control = 0x00
        self.bus.write_i2c_block_data(self.device_address, 0x10, [control])
        data = self.bus.read_i2c_block_data(self.device_address, 0x10, 1)
        # Should be 0, since this is what we just send
        return data[0]

    def set_voltage(self, voltage):
        # Todo, check value is within range
        decivoltage = int(voltage * 1024)
        high_byte = decivoltage >> 8
        low_byte = decivoltage % 256
        data = [low_byte, high_byte]
        self.bus.write_i2c_block_data(self.device_address, 0x21, data)

    def set_current(self, current):
        # Todo, check value is within range
        # scaled_current = int(current * 1024)
        high_byte = 0  # Current limit is in integer Amps, high byte never used
        low_byte = int(current)
        data = [low_byte, high_byte]
        # data = [2, 0]
        self.bus.write_i2c_block_data(self.device_address, 0x46, data)


if __name__ == '__main__':
    xp = XP_HPA_PS()
    xp.write_enable()
    # xp.store_user_all()
    xp.operation(turn_on=True)
    xp.clear_errors()

    print('Comm status: {}'.format(xp.read_communication_status()))
    # xp.configure_user_settings(cfg_fan_off=True)
    # xp.configure_user_settings(cfg_remote_inhibit_logic=False)
    print('User configuration: {}'.format(xp.read_user_configuration()))
    print('Comm status: {}'.format(xp.read_communication_status()))
    print('Voltage output status: {}'.format(xp.read_voltage_out_status()))
    print('Manufacturer: {}'.format(xp.read_manufacturer()))
    print('Model: {}'.format(xp.read_model()))
    print('Serial: {}'.format(xp.read_serial_nr()))
    temps = xp.read_temperatures()
    print('Primary temp sensor: {}C. Secondary: {}C'.format(temps[1], temps[0]))

    print('Fan speeds: {}'.format(xp.read_fan_speeds()))
    print('Input voltage: {}'.format(xp.read_input_voltage()))

    xp.set_voltage(1)
    xp.set_current(1)
    # xp.set_voltage(0.5)

    time.sleep(1)
    print('PS Voltage: {}V'.format(xp.read_actual_voltage()))
    print('PS Current: {}A'.format(xp.read_actual_current()))
    print()
    print('Status byte: {}'.format(xp.read_status_byte()))
    print('Voltage output status: {}'.format(xp.read_voltage_out_status()))
    print('Current output status: {}'.format(xp.read_current_out_status()))
    print('Comm status: {}'.format(xp.read_communication_status()))
    print()
