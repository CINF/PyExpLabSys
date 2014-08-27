import serial
import time
import struct

class Brooks():

    def __init__(self, port='/dev/ttyUSB2'):
        self.devices = ['3F2320902001'] # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        self.f = serial.Serial(port, 19200)
        self.f.parity = serial.PARITY_ODD
        self.f.bytesize = serial.EIGHTBITS
        self.f.stopbits = serial.STOPBITS_ONE
        deviceid = self.comm('8280000000000b06' + self.pack(self.devices[0][-8:]))
        long_address = '0a5a' + deviceid[-6:]  # 0a5a should in principle also be extracted
        self.long_address = long_address

    def pack(self, input_string):
        #This function lacks basic error checking....
        klaf = ''
        for s in input_string:
            klaf += bin((ord(s) % 128) % 64)[2:].zfill(6)
        result = ''
        for i in range(0, 6):
            result = result + hex(int('' + klaf[i * 8:i * 8 + 8], 2))[2:].zfill(2)
        return result

    def crc(self, command):
        """ Calculate crc value of command """
        i = 0
        while command[i:i + 2] == 'FF':
            i += 2
        command = command[i:]
        n = len(command)
        result = 0
        for i in range(0, (n/2)):
            byte_string = command[i*2:i*2+2]
            byte = int(byte_string, 16)
            result = byte ^ result
        return hex(result)

    def comm(self, command):
        check = str(self.crc(command))
        check = check[2:].zfill(2)
        final_com = 'FFFFFFFF' + command + check
        bin_comm = ''
        for i in range(0, len(final_com) / 2):
            bin_comm += chr(int(final_com[i * 2:i * 2 + 2],16))
        error = True
        while error is True:
            self.f.write(bin_comm + chr(0))
            time.sleep(0.1)
            s = self.f.read(self.f.inWaiting())
            st = ''
            for i in range(0, len(s)):
                char = hex(ord(s[i]))[2:].zfill(2)
                if not char.upper() == 'FF':
                    st = st + char
            try:
                delimiter = st[0:2]
                address = st[2:12]
                command = st[12:14]
                byte_count = int(st[14:16], 16)
                response = st[16:16 + 2 * byte_count]
                error = False
            except ValueError:
                error = True  # Send string again
        return(response)

    def read_flow(self):
        response = self.comm('82' + self.long_address + '0100')
        try:  # TODO: This should be handled be re-sending command
            status_code = response[0:4]
            unit_code = int(response[4:6], 16)
            flow_code = response[6:]
            byte0 = chr(int(flow_code[0:2], 16))
            byte1 = chr(int(flow_code[2:4], 16))
            byte2 = chr(int(flow_code[4:6], 16))
            byte3 = chr(int(flow_code[6:8], 16))
            flow = struct.unpack('>f', byte0 + byte1 + byte2 + byte3)
            value = flow[0]
        except ValueError:
            value = -1
            unit_code = 171  # Satisfy assertion check, since in this case we know what is wrong
        assert(unit_code == 171)  # Flow controller should always be set to mL/min
        return(value)

    def read_full_range(self):
        response = self.comm('82' + self.long_address + '980106')#Command 152
        #Double check what gas-selection code really means... currently 01 is used
        status_code = response[0:4]
        unit_code = int(response[4:6],16)
        assert(unit_code == 171)#Flow controller should always be set to mL/min

        flow_code = response[6:]
        byte0 = chr(int(flow_code[0:2], 16))
        byte1 = chr(int(flow_code[2:4], 16))
        byte2 = chr(int(flow_code[4:6], 16))
        byte3 = chr(int(flow_code[6:8], 16))
        max_flow = struct.unpack('>f', byte0 + byte1 + byte2 + byte3)
        return(max_flow[0])

    def set_flow(self, flowrate):
        ieee = struct.pack('>f', flowrate)
        ieee_flowrate = ''
        for i in range(0, 4):
            ieee_flowrate += hex(ord(ieee[i]))[2:].zfill(2)
        #39 = unit code for percent
        #FA = unit code for 'same unit as flowrate measurement'
        response = self.comm('82' + self.long_address + 'ec05' + 'FA' + ieee_flowrate)
        status_code = response[0:4]
        unit_code = int(response[4:6],16)

if __name__ == '__main__':
    devices = ['3F2320902001']
    brooks = Brooks()
    print brooks.long_address
    print brooks.read_flow()
    print brooks.read_full_range()
    print brooks.set_flow(0.0)
