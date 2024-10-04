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
    6: 'psi', 7: 'bar', 8: 'mbar', 11: 'Pa', 12: 'kPa', 13: 'Torr', 171: 'ml/min',
    }

class Brooks(object):
    """ Driver for Brooks s-protocol """

    def __init__(self, device=None, port='/dev/ttyUSB0', controller='mfc', mode='absolute', echo=False):
        self.ser = serial.Serial(port, 19200)
        self.ser.parity = serial.PARITY_ODD
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.stopbits = serial.STOPBITS_ONE


        #         time.sleep(1)
        # for i in range(0, 20):
        # time.sleep(0.1)
        #            print(self.ser.read(self.ser.inWaiting()))
        # exit()
        self.echo = echo
        self.controller = controller
        if not mode in ['absolute', 'gauge']:
            raise ValueError('"mode" must be either "gauge" or "absolute". Not used for MFCs')
        self.mode = mode
        self.device = device
        # print('Pack device... ' + self.pack(device[-8:]))
        deviceid = self.comm('8280000000000b06' + self.pack(device[-8:]))

        # print('Device id: ' + deviceid)
        manufactor_code = '0a'
        #print(manufactor_code)
        #device_type = deviceid[12:14]
        device_type = deviceid[8:10] ### According to enhanced S-protocol - check with rasppi35
        #print('Device type:', device_type)
        # print('Device type: ' + device_type)
        #print(deviceid[-6:])
        long_address = manufactor_code + device_type + deviceid[-6:]
        self.long_address = long_address
        print('Long address: ' + self.long_address)
        #self.full_range = self.read_full_range() # Breaks on VHP FIXME

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
        # print('CRC ({})'.format(self.device))
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
        # print(result, hex(result))
        return hex(result)

    def comm(self, command):
        """ Implements low-level details of the s-protocol """
        # print('Comm ({})'.format(self.device))
        orig_command = command
        
        # print(command)
        check = str(self.crc(command))
        check = check[2:].zfill(2)
        
        final_com = 'FFFFFFFF' + command + check
        # print('Final comm: ' + final_com)
        bin_comm = ''
        for i in range(0, len(final_com) // 2):
            bin_comm += chr(int(final_com[i * 2 : i * 2 + 2], 16))
        bin_comm += chr(0)
        bytes_for_serial = b(bin_comm)
        error = 1
        while (error > 0) and (error < 10):
            # 0print('def comm - Bytes: ' + repr(bytes_for_serial))
            self.ser.write(bytes_for_serial)
            time.sleep(0.2)
            #print('bytes in waiting: {}'.format(self.ser.inWaiting()))
            s = self.ser.read(self.ser.inWaiting())
            if s == b'\x00':
                raise IOError('No comms with instrument')
            #print(repr(s))
            # print(' *** s: ' + str(s))
            # print(len(s))
            st = ''
            for i in range(0, len(s)):
                # char = hex(ord(s[i]))[2:].zfill(2)
                # char = hex(s[i])[2:].zfill(2)
                char = hex(indexbytes(s, i))[2:].zfill(2)
                #print(i, char)
                st += char
                #if not char.upper() == 'FF':
                #    st = st + char
                #else:
                #    print(i, 'FF')
            #print('__st: {}'.format(st))
            st = st.lstrip('ff')
            print(st)
            try:
                # delimiter = st[0:2]
                # address = st[2:12]
                command = st[12:14]
                # print('__command: {}'.format(command))
                byte_count = int(st[14:16], 16)
                # print('__byte_count: {}'.format(byte_count))
                response = st[16 : 16 + 2 * byte_count]
                # print('__response: {}'.format(response))
                error = 0
            except ValueError:
                error = error + 1
                response = 'Error'
        if error == 10:
            print('Brooks communication error!')
        if self.echo:
            print('Response of command "{}": {}'.format(orig_command, response))
        return response

    def read_flow(self):
        """ Read the current flow-rate """
        #if self.controller == 'pc': # Pressure controller
        #    return self.read_pressure()
        print('Read flow ({})'.format(self.device))
        response = self.comm('82' + self.long_address + '0100')
        try:  # TODO: This should be handled be re-sending command
            # status_code = response[0:4]
            unit_code = int(response[4:6], 16)
            flow_code = response[6:]
            byte0 = chr(int(flow_code[0:2], 16))
            byte1 = chr(int(flow_code[2:4], 16))
            byte2 = chr(int(flow_code[4:6], 16))
            byte3 = chr(int(flow_code[6:8], 16))
            flow = struct.unpack('>f', b(byte0 + byte1 + byte2 + byte3))
            value = flow[0]
        except ValueError:
            value = -1
            unit_code = 171  # Satisfy assertion check, we know what is wrong
        #print('Unit code: ' + repr(unit_code))
        #assert unit_code == 171  # Flow unit should always be mL/min (unless it is a PC)
        # Gauge or not
        # TODO: correction only valid for unit "bar"
        # TODO: this part breaks the except ValueError for the MFCs
        if self.controller == 'pc' and self.mode == 'gauge':
            value += 1
            if self.unit != 'bar':
                print('!!! Warning: pressure reading "gauge" correction only implemented for unit "bar"')
        return value

    def read_setpoint(self):
        """ Read setpoint """
        print('Reading setpoint')
        response = self.comm('82' + self.long_address + 'eb00')
        print(response, len(response))
        status = response[0:4]
        unit_code = int(response[4:6], 16)
        assert unit_code == 57 # percent
        flow_code = response[6:14]
        byte0 = chr(int(flow_code[0:2], 16))
        byte1 = chr(int(flow_code[2:4], 16))
        byte2 = chr(int(flow_code[4:6], 16))
        byte3 = chr(int(flow_code[6:8], 16))
        flow_percent = struct.unpack('>f', b(byte0 + byte1 + byte2 + byte3))
        percent = (flow_percent[0], '%')
        print(percent)

        unit_code = int(response[14:16], 16)
        print(unit_code)
        unit = UNIT_CODES[unit_code]
        flow_code = response[16:24]
        byte0 = chr(int(flow_code[0:2], 16))
        byte1 = chr(int(flow_code[2:4], 16))
        byte2 = chr(int(flow_code[4:6], 16))
        byte3 = chr(int(flow_code[6:8], 16))
        flow_unit = struct.unpack('>f', b(byte0 + byte1 + byte2 + byte3))[0]
        # Gauge or not
        # TODO: correction only valid for unit "bar"
        if self.controller == 'pc' and self.mode == 'gauge':
            flow_unit += 1
            if unit != 'bar':
                print('!!! Warning: pressure reading "gauge" correction only implemented for unit "bar"')
        units = (flow_unit, unit)
        return (percent, units)

    def read_process_gas(self, number=6):
        if number < 1 or number > 6: # A pressure controller only responded to 1 and 2
            raise ValueError('Number must be in range [1, 6]')
        response = self.comm('82' + self.long_address + '9601' + hex(number)[2:].zfill(2))
        response = response.rstrip('0')[6:]
        gas = ''
        for i in range(int(len(response)/2)):
            gas += chr(int(response[i*2:(i+1)*2], 16))
        return gas
    
    def read_full_scale_pressure_range(self):
        """ Report the configured full scale pressure range (cmd #159 - page 67)"""
        print('Read full range (pressure)')
        # Command 159 - process gas 1 (probably 'Air')
        response = self.comm('82' + self.long_address + '9f0101')
        status_code = response[:4]
        unit_code = int(response[4:6], 16)
        unit = UNIT_CODES[unit_code]
        self.unit = unit
        pressure_code = response[6:]
        byte0 = chr(int(pressure_code[0:2], 16))
        byte1 = chr(int(pressure_code[2:4], 16))
        byte2 = chr(int(pressure_code[4:6], 16))
        byte3 = chr(int(pressure_code[6:8], 16))
        max_flow = struct.unpack('>f', b(byte0 + byte1 + byte2 + byte3))[0]
        # Gauge or not
        # TODO: correction only valid for unit "bar"
        if self.controller == 'pc' and self.mode == 'gauge':
            max_flow += 1
            if unit != 'bar':
                print('!!! Warning: pressure reading "gauge" correction only implemented for unit "bar"')
        print('Full scale: {:.3f} {}'.format(max_flow, unit))
        return max_flow, unit

    def read_full_range(self):
        """
        Report the full range of the device
        Apparantly this does not work for SLA-series...
        """
        if self.controller == 'pc':
            return self.read_full_scale_pressure_range()
        #print('Read full range ({})'.format(self.device))
        response = self.comm('82' + self.long_address + '980106')  # Command 152
        #print(response)
        # Double check what gas-selection code really means...
        # currently 01 is used
        # status_code = response[0:4]
        unit_code = int(response[4:6], 16)
        assert unit_code == 171  # Flow controller should always be set to mL/min
        self.unit = 'ml/min'

        flow_code = response[6:]
        byte0 = chr(int(flow_code[0:2], 16))
        byte1 = chr(int(flow_code[2:4], 16))
        byte2 = chr(int(flow_code[4:6], 16))
        byte3 = chr(int(flow_code[6:8], 16))
        max_flow = struct.unpack('>f', b(byte0 + byte1 + byte2 + byte3))[0]
        print('Full scale: {:.3f} {}'.format(max_flow, self.unit))
        return max_flow

    def set_flow(self, flowrate):
        """ Set the setpoint of the flow (given in selected unit)"""
        # Gauge or not
        # TODO: correction only valid for unit "bar"
        if self.controller == 'pc' and self.mode == 'gauge':
            flowrate -= 1
            if self.unit != 'bar':
                print('!!! Warning: pressure reading "gauge" correction only implemented for unit "bar"')
        #print('Set flow ({}): {}'.format(self.device, flowrate))
        ieee = struct.pack('>f', flowrate)

        # Python3
        ieee_flowrate = ''
        for i in range(0, 4):
            ieee_flowrate += hex(ieee[i])[2:].zfill(2)
            # print(ieee_flowrate)

        # 39 = unit code for percent
        # FA = unit code for 'same unit as flowrate measurement'
        response = self.comm('82' + self.long_address +
                             'ec05' + 'FA' + ieee_flowrate)
        status_code = response[0:4]
        unit_code = int(response[4:6], 16)
        return True

    def set_pressure_unit(self, unit='bar'):
        """ Configure the unit of pressure """
        for code, _unit in UNIT_CODES.items():
            if _unit == unit:
                unit_code = hex(code).lstrip('0x').zfill(2)
                response = self.comm('82' + self.long_address + 'c601' + unit_code)
                #print(response)
                return
        raise ValueError('Unit ({}) not recognized. Allowed: {}'.format(unit, UNIT_CODES))


if __name__ == '__main__':
    #BROOKS = Brooks('01C40201328', controller='pc', mode='absolute')
    BROOKS = Brooks('F25600002', controller='mfc')
    print(BROOKS.read_setpoint())
    print(BROOKS.read_full_range())
    print(BROOKS.read_flow())
    
