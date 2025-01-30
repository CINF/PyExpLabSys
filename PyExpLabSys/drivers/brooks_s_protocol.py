""" Driver for Brooks s-protocol """
from __future__ import print_function
import time
import struct
import logging
import serial
from six import b, indexbytes
from PyExpLabSys.common.supported_versions import python2_and_3

# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

UNIT_CODES = {
    6: 'psi',
    7: 'bar',
    8: 'mbar',
    11: 'Pa',
    12: 'kPa',
    13: 'Torr',
    171: 'ml/min',
}


def code_to_ieee754(flow_code):
    """ Takes the 32-bit hex string and converts it to IEEE 754 floating point format"""
    byte0 = chr(int(flow_code[0:2], 16))
    byte1 = chr(int(flow_code[2:4], 16))
    byte2 = chr(int(flow_code[4:6], 16))
    byte3 = chr(int(flow_code[6:8], 16))
    flow = struct.unpack('>f', b(byte0 + byte1 + byte2 + byte3))
    value = flow[0]
    return value


class Brooks(object):
    """ Driver for Brooks s-protocol """

    def __init__(
        self,
        device=None,
        port='/dev/ttyUSB0',
        controller='mfc',
        mode='absolute',
        debug=False,
        ignore_errors=False,
        suppress_info=False,
    ):
        self.ser = serial.Serial(port, 19200)
        self.ser.parity = serial.PARITY_ODD
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.stopbits = serial.STOPBITS_ONE

        self.assertions = False
        self.ignore_errors = ignore_errors
        self.suppress_info = True
        self.debug = debug
        if controller.lower() == 'pc':
            self.controller = 'pc'
            self.unit_code = 7  # bar
            self.unit = 'bar'
        else:
            self.controller = 'mfc'
            self.unit_code = 171  # ml/min
            self.unit = 'ml/min'
        if not mode in ['absolute', 'gauge']:
            raise ValueError(
                '"mode" must be either "gauge" or "absolute". Not used for MFCs'
            )
        self.mode = mode
        self.device = device

        deviceid = self.comm('8280000000000b06' + self.pack(device[-8:]))
        manufactor_code = '0a'
        device_type = deviceid[8:10]
        long_address = manufactor_code + device_type + deviceid[-6:]
        self.long_address = long_address
        if debug:
            print('Long address: ' + self.long_address)
        self.info = self.read_sensor_information()
        self.full_range = self.read_full_range()
        # assert units
        vp, vu = self.read_setpoint()  # value percent and value unit
        if UNIT_CODES[self.unit_code] != vu[1]:
            print(
                ' *** Only units [bar] or [ml/min] are allowed in this driver version!  ***'
            )
            print(
                ' *** Either change units (e.g. with set_pressure_unit() or edit driver ***'
            )
        self.assertions = True
        self.suppress_info = suppress_info
        if not self.suppress_info:
            print(
                'Connected to device "{}" as {}'.format(
                    self.device, self.controller.upper()
                )
            )
            print('Known info:')
            print('\tUnit code: {}'.format(self.info['unit_code']))
            try:
                unit = UNIT_CODES[self.info['unit_code']]
            except KeyError:
                unit = 'unknown unit translation'  # unit_code is not in UNIT_CODES
            print('\tSerial number: {}'.format(self.info['serial_number']))
            print('\tSensor upper limit: {} {}'.format(self.info['upper_limit'], unit))
            print('\tSensor lower limit: {} {}'.format(self.info['lower_limit'], unit))
            print(
                '\tSensor minimum span: {} {}'.format(self.info['minimum_span'], unit)
            )
            print('\tFull range: {} {}\r\n'.format(*self.full_range))

    def pack(self, input_string):
        """ Turns a string in packed-ascii format """
        # This function lacks basic error checking....
        klaf = ''
        for s in input_string:
            klaf += bin((ord(s) % 128) % 64)[2:].zfill(6)
        result = ''
        for i in range(0, 6):
            result = result + hex(int('' + klaf[i * 8 : i * 8 + 8], 2))[2:].zfill(2)
        return result

    def crc(self, command):
        """ Calculate crc value of command """
        i = 0
        while command[i : i + 2] == 'FF':
            i += 2
        command = command[i:]
        n = len(command)
        result = 0
        for i in range(0, (n // 2)):
            byte_string = command[i * 2 : i * 2 + 2]
            byte = int(byte_string, 16)
            result = byte ^ result
        return hex(result)

    def comm(self, command):
        """ Implements low-level details of the s-protocol """
        check = str(self.crc(command))
        check = check[2:].zfill(2)

        final_com = 'FFFFFFFF' + command + check
        bin_comm = ''
        for i in range(0, len(final_com) // 2):
            bin_comm += chr(int(final_com[i * 2 : i * 2 + 2], 16))
        bin_comm += chr(0)
        bytes_for_serial = b(bin_comm)
        error = 1
        while (error > 0) and (error < 10):
            self.ser.write(bytes_for_serial)
            time.sleep(0.2)
            s = self.ser.read(self.ser.inWaiting())
            if s == b'\x00':
                raise IOError('No comms with instrument')
            st = ''
            for i in range(0, len(s)):
                char = hex(indexbytes(s, i))[2:].zfill(2)
                st += char
            if self.debug:
                print('__raw hex response: {}'.format(st))
            st = st.lstrip('ff')
            try:
                delimiter = st[0:2]
                address = st[2:12]  # 5 bytes for long format (delimiter 86)
                command = st[12:14]
                byte_count = int(st[14:16], 16)
                status = st[16:20]
                response = st[16 : 16 + 2 * byte_count]
                # Error indicator
                if status != '0000':
                    self.interpret_status(status)
                error = 0
            except ValueError:
                error = error + 1
                response = 'Error'
        if self.assertions:
            assert delimiter == '86'
        if error == 10:
            print('Brooks communication error!')
        if self.debug:
            print('__delimiter: ', delimiter)
            print('__adress: ', address)
            print('__command: {}'.format(command))
            print('__byte_count: {}'.format(byte_count))
            print('__status_byte: ', status)
            print('__response: {}'.format(response))
            print('Response of command "{}": {}'.format(final_com, response))
        return response

    def interpret_status(self, status):
        """ Interpret the status byte """
        if self.ignore_errors:
            return
        print('*****', end='')
        print('Non-zero status bytes: ', end='')
        byte_1 = int(status[0:2], 16)
        byte_1 = bin(byte_1)[2:].zfill(8)
        byte_2 = int(status[2:4], 16)
        byte_2 = bin(byte_2)[2:].zfill(8)
        print('{} {} '.format(byte_1, byte_2), end='')
        if byte_1[-8] == '1':
            print('Communication error: ', end='')
            if byte_1[-7] == '1':
                print(' - parity error (hex C0)', end='')
            if byte_1[-6] == '1':
                print(' - overrun error (hex A0)', end='')
            if byte_1[-5] == '1':
                print(' - framing error (hex 90)', end='')
            if byte_1[-4] == '1':
                print(' - checksum error (hex 88)', end='')
            if byte_1[-3] == '1':
                print(' - Reserved (hex 84)', end='')
            if byte_1[-2] == '1':
                print(' - Rx buffer overflow (hex 82)', end='')
            if byte_1[-1] == '1':
                print(' - Undefined', end='')
            if byte_2 != '00000000':
                print(
                    'Status byte 2 reported non-zero bits that should have all been zero!',
                    end='',
                )
        else:
            print('Command error: ', end='')
            byte_1 = int(byte_1, 2)
            if byte_1 == 0:
                print(' - Non command specific error', end='')
            if byte_1 == 1:
                print(' - Undefined', end='')
            if byte_1 == 2:
                print(' - Invalid selection', end='')
            if byte_1 == 3:
                print(' - Passed parameter too large', end='')
            if byte_1 == 4:
                print(' - Passed parameter too small', end='')
            if byte_1 == 5:
                print(' - Incorrect byte count', end='')
            if byte_1 == 6:
                print(' - Transmitter specific command error', end='')
            if byte_1 == 7:
                print(' - In write-protect mode', end='')
            if byte_1 > 7 and byte_1 < 16:
                print(' - Command specific errors - check manual', end='')
            if byte_1 == 16:
                print(' - Access restricted', end='')
            if byte_1 == 32:
                print(' - Device is busy', end='')
            if byte_1 == 64:
                print(' - Command not implemented', end='')
            if byte_2[-8] == '1':
                print('Device malfunction', end='')
            if byte_2[-7] == '1':
                print('Configuration changed', end='')
            if byte_2[-6] == '1':
                print('Cold start', end='')
            if byte_2[-5] == '1':
                print('More status available (cmd 48 - check manual)', end='')
            if byte_2[-4] == '1':
                print('Primary variable analog output fixed', end='')
            if byte_2[-3] == '1':
                print('Primary variable analog output saturated', end='')
            if byte_2[-2] == '1':
                print('Non primary variable out of range', end='')
            if byte_2[-1] == '1':
                print('Primary variable out of range', end='')
        print('*****')

    def read_sensor_information(self):
        """Read primary variable sensor information (cmd 14)
        It would seem the unit in this command is hard-coded into the device."""
        response = self.comm('82' + self.long_address + '0e00')
        try:
            status_code = response[0:4]
            serial_number = response[4:10]
            unit_code = int(response[10:12], 16)
            upper_limit = code_to_ieee754(response[12:20])
            lower_limit = code_to_ieee754(response[20:28])
            minimum_span = code_to_ieee754(response[28:36])
        except ValueError:
            serial_number = None
            unit_code = None
            upper_limit = None
            lower_limit = None
            minimum_span = None
        return {
            'serial_number': serial_number,
            'unit_code': unit_code,
            'upper_limit': upper_limit,
            'lower_limit': lower_limit,
            'minimum_span': minimum_span,
        }

    def read_flow(self):
        """ Read the current flow-rate """
        response = self.comm('82' + self.long_address + '0100')
        try:  # TODO: This should be handled be re-sending command
            status_code = response[0:4]
            unit_code = int(response[4:6], 16)
            flow_code = response[6:]
            value = code_to_ieee754(flow_code)
        except ValueError:
            value = -1
            unit_code = self.unit_code  # Satisfy assertion check, we know what is wrong
        if self.assertions:
            assert unit_code == self.unit_code
        # Gauge or not
        # TODO: correction only valid for unit "bar"
        if self.controller == 'pc' and self.mode == 'gauge':
            value += 1
            if self.unit != 'bar':
                print(
                    '!!! Warning: pressure reading "gauge" correction only implemented for unit "bar"'
                )
        if not self.suppress_info:
            print(
                'Read flow ({}): {} {}'.format(
                    self.device, value, UNIT_CODES[unit_code]
                )
            )
        return value

    def read_setpoint(self):
        """ Read setpoint """
        response = self.comm('82' + self.long_address + 'eb00')
        status = response[0:4]
        # as percent
        unit_code = int(response[4:6], 16)
        assert unit_code == 57  # always 57 (percent)
        flow_code = response[6:14]
        flow_percent = code_to_ieee754(flow_code)
        percent = (flow_percent, '%')
        # as unit
        unit_code = int(response[14:16], 16)
        if self.assertions:
            assert unit_code == self.unit_code
        unit = UNIT_CODES[unit_code]
        flow_code = response[16:24]
        flow_unit = code_to_ieee754(flow_code)
        # Gauge or not
        # TODO: correction only valid for unit "bar"
        if self.controller == 'pc' and self.mode == 'gauge':
            flow_unit += 1
            if unit != 'bar':
                print(
                    '!!! Warning: pressure reading "gauge" correction only implemented for unit "bar"'
                )
        units = (flow_unit, unit)
        if not self.suppress_info:
            print(
                'Setpoint ({}): {:.3f} {} / {:.3f} %'.format(
                    self.device, flow_unit, unit, flow_percent
                )
            )
        return (percent, units)

    def read_process_gas(self, number=6):
        if number < 1 or number > 6:  # A pressure controller only responded to 1 and 2
            raise ValueError('Number must be in range [1, 6]')
        response = self.comm(
            '82' + self.long_address + '9601' + hex(number)[2:].zfill(2)
        )
        response = response.rstrip('0')[6:]
        gas = ''
        for i in range(int(len(response) / 2)):
            gas += chr(int(response[i * 2 : (i + 1) * 2], 16))
        return gas

    def read_full_scale_pressure_range(self):
        """ Report the configured full scale pressure range (cmd #159 - page 67)"""
        # Command 159 - process gas 1 (probably 'Air')
        response = self.comm('82' + self.long_address + '9f0101')
        status_code = response[:4]
        unit_code = int(response[4:6], 16)
        unit = UNIT_CODES[unit_code]
        self.unit = unit
        pressure_code = response[6:]
        max_flow = code_to_ieee754(pressure_code)
        # Gauge or not
        # TODO: correction only valid for unit "bar"
        if self.controller == 'pc' and self.mode == 'gauge':
            max_flow += 1
            if unit != 'bar':
                print(
                    '!!! Warning: pressure reading "gauge" correction only implemented for unit "bar"'
                )
        if not self.suppress_info:
            print('Full scale ({}): {:.3f} {}'.format(self.device, max_flow, unit))
        return max_flow, unit

    def read_full_range(self):
        """
        Report the full range of the device
        Apparantly this does not work for SLA-series...
        """
        if self.controller == 'pc':
            return self.read_full_scale_pressure_range()
        response = self.comm('82' + self.long_address + '980101')  # Command 152
        # Double check what gas-selection code really means...
        # currently 01 is used
        if len(response) < 14:
            print("SLA MFC apparently don't report full range")
            return None, None
        status_code = response[0:4]
        unit_code = int(response[4:6], 16)
        print('unit code: ', unit_code)
        if self.assertions:
            assert unit_code == 171  # Flow controller should always be set to mL/min

        flow_code = response[6:]
        max_flow = code_to_ieee754(flow_code)
        if not self.suppress_info:
            print(
                'Full scale ({}): {:.3f} {}'.format(
                    self.device, max_flow, UNIT_CODES[unit_code]
                )
            )
        return max_flow, self.unit

    def set_flow(self, flowrate):
        """ Set the setpoint of the flow (given in selected unit)"""
        # Gauge or not
        # TODO: correction only valid for unit "bar"
        if self.controller == 'pc' and self.mode == 'gauge':
            flowrate -= 1
            if self.unit != 'bar':
                print(
                    '!!! Warning: pressure reading "gauge" correction only implemented for unit "bar"'
                )
        if not self.suppress_info:
            print('Set flow ({}): {} {}'.format(self.device, flowrate, self.unit))
        ieee = struct.pack('>f', flowrate)

        # Python3
        ieee_flowrate = ''
        for i in range(0, 4):
            ieee_flowrate += hex(ieee[i])[2:].zfill(2)

        # 39 = unit code for percent
        # FA = unit code for 'same unit as flowrate measurement'
        response = self.comm('82' + self.long_address + 'ec05' + 'FA' + ieee_flowrate)
        status_code = response[0:4]
        unit_code = int(response[4:6], 16)
        return True

    def set_pressure_unit(self, unit='bar'):
        """ Configure the unit of pressure """
        for code, _unit in UNIT_CODES.items():
            if _unit == unit:
                unit_code = hex(code).lstrip('0x').zfill(2)
                response = self.comm('82' + self.long_address + 'c601' + unit_code)
                return
        raise ValueError(
            'Unit ({}) not recognized. Allowed: {}'.format(unit, UNIT_CODES)
        )


if __name__ == '__main__':
    # BROOKS = Brooks('01C12101411', controller='pc', mode='absolute', debug=False, ignore_errors=True)
    BROOKS = Brooks('F25600002', controller='mfc')
    # BROOKS.set_pressure_unit('bar')
    setpoint = BROOKS.read_setpoint()
    print(setpoint)
    fullrange = BROOKS.read_full_range()
    print(fullrange)
    flow = BROOKS.read_flow()
    print(flow)
