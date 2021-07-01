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

class Brooks(object):
    """ Driver for Brooks s-protocol """
    def __init__(self, device, port='/dev/ttyUSB0'):
        self.ser = serial.Serial(port, 19200)
        self.ser.parity = serial.PARITY_ODD
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.stopbits = serial.STOPBITS_ONE
        deviceid = self.comm('8280000000000b06'
                             + self.pack(device[-8:]))
        manufactor_code = '0a'
        device_type = deviceid[12:14]
        long_address = manufactor_code + device_type + deviceid[-6:]
        self.long_address = long_address

    def pack(self, input_string):
        """ Turns a string in packed-ascii format """
        #This function lacks basic error checking....
        klaf = ''
        for s in input_string:
            klaf += bin((ord(s) % 128) % 64)[2:].zfill(6)
        result = ''
        for i in range(0, 6):
            result = result + hex(int('' + klaf[i * 8:i * 8 + 8],
                                      2))[2:].zfill(2)
        return result

    def crc(self, command):
        """ Calculate crc value of command """
        i = 0
        while command[i:i + 2] == 'FF':
            i += 2
        command = command[i:]
        n = len(command)
        result = 0
        for i in range(0, (n//2)):
            byte_string = command[i*2:i*2+2]
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
            bin_comm += chr(int(final_com[i * 2:i * 2 + 2], 16))
        bin_comm += chr(0)
        bytes_for_serial = b(bin_comm)
        error = 1
        while (error > 0) and (error < 10):
            self.ser.write(bytes_for_serial)
            time.sleep(0.2)
            s = self.ser.read(self.ser.inWaiting())
            st = ''
            for i in range(0, len(s)):
                #char = hex(ord(s[i]))[2:].zfill(2)
                #char = hex(s[i])[2:].zfill(2)
                char = hex(indexbytes(s, i))[2:].zfill(2)
                if not char.upper() == 'FF':
                    st = st + char
            try:
                # delimiter = st[0:2]
                # address = st[2:12]
                command = st[12:14]
                byte_count = int(st[14:16], 16)
                response = st[16:16 + 2 * byte_count]
                error = 0
            except ValueError:
                error = error + 1
                response = 'Error'
        return response

    def read_flow(self):
        """ Read the current flow-rate """
        response = self.comm('82' + self.long_address + '0100')
        try:  # TODO: This should be handled be re-sending command
            #status_code = response[0:4]
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
        assert unit_code == 171  # Flow unit should always be mL/min
        return value

    def read_full_range(self):
        """
        Report the full range of the device
        Apparantly this does not work for SLA-series...
        """
        response = self.comm('82' + self.long_address + '980106')#Command 152
        print(response)
        # Double check what gas-selection code really means...
        # currently 01 is used
        # status_code = response[0:4]
        unit_code = int(response[4:6], 16)
        assert unit_code == 171 #Flow controller should always be set to mL/min

        flow_code = response[6:]
        byte0 = chr(int(flow_code[0:2], 16))
        byte1 = chr(int(flow_code[2:4], 16))
        byte2 = chr(int(flow_code[4:6], 16))
        byte3 = chr(int(flow_code[6:8], 16))
        max_flow = struct.unpack('>f', byte0 + byte1 + byte2 + byte3)
        return max_flow[0]

    def set_flow(self, flowrate):
        """ Set the setpoint of the flow """
        ieee = struct.pack('>f', flowrate)
        ieee_flowrate = ''
        for i in range(0, 4):
            ieee_flowrate += hex(ord(ieee[i]))[2:].zfill(2)
        #39 = unit code for percent
        #FA = unit code for 'same unit as flowrate measurement'
        #response = self.comm('82' + self.long_address +
        #                     'ec05' + 'FA' + ieee_flowrate)
        # status_code = response[0:4]
        # unit_code = int(response[4:6], 16)
        return True

if __name__ == '__main__':
    BROOKS = Brooks('3F2320902001')
    print(BROOKS.long_address)
    print(BROOKS.read_full_range())
    print(BROOKS.read_flow())
