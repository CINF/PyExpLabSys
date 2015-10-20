# -*- coding: utf-8 -*-
#!/usr/local/bin/python
#
# ----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 42):
# <phk@FreeBSD.ORG> wrote this file.  As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return.   Poul-Henning Kamp
# ----------------------------------------------------------------------------
#

from __future__ import print_function

# You need pySerial 
import serial

import math

#######################################################################
# These are the variables I have managed to identify
# Submissions welcome.

kamstrup_382_var = {

    0x0001: "Energy in",
    0x0002: "Energy out",

    0x000d: "Energy in hi-res",
    0x000e: "Energy out hi-res",

    0x041e: "Voltage p1",
    0x041f: "Voltage p2",
    0x0420: "Voltage p3",

    0x0434: "Current p1",
    0x0435: "Current p2",
    0x0436: "Current p3",

    0x0438: "Power p1",
    0x0439: "Power p2",
    0x043a: "Power p3",
}

kamstrup_302_var = {'Date': 1003,
                     'Clock': 1002,
                     'InfoCode': 99,
                     'InfoEventCounter': 113,
                     'HourCounter': 1004,
                     'Energy1': 60,
                     'Energy3': 63,
                     'Energy8': 97,
                     'Energy9': 110,
                     'Volume1': 68,
                     'Temp1': 86,
                     'Temp2': 87,
                     'Temp1-Temp2': 89,
                     'Flow1': 74,
                     'Power1': 80,
                     'V1HighRes': 239,
                     'E1HighRes': 266,
                     'E3HighRes': 267,
                     'LogDaySetUp': 98,
                     'AvrTemp1(y)': 146,
                     'AvrTemp2(y)': 147,
                     'AvrTemp1(m)': 149,
                     'AvrTemp2(m)': 150,
                     'AutoIntT1Averrage': 229,
                     'AutoIntT2Averrage': 230,
                     'MaxFlow1Date(y)': 123,
                     'MaxFlow1(y)': 124,
                     'MaxPower1Date(y)': 127,
                     'MaxPower1(y)': 128,
                     'MaxFlow1Date(m)': 138,
                     'MaxFlow1(m)': 139,
                     'MaxPower1Date(m)': 142,
                     'MaxPower1(m)': 143,
                     'Xday': 98,
                     'ConfNo1': 153,
                     'ConfNo2': 168,
                     'SerialNumber': 1001,
                     'MeterNo(high)': 112,
                     'MeterNumber(low)': 1010,
                     'MeterType': 1005,
                     'MBusBotDispPriAddr': 184,
                     'MBusBotDispSecAddr': 185,
                     'CheckSum': 154,
                     'Infohour': 175,
                     }


#######################################################################
# Units, provided by Erik Jensen

units = {
    0: '', 1: 'Wh', 2: 'kWh', 3: 'MWh', 4: 'GWh', 5: 'j', 6: 'kj', 7: 'Mj',
    8: 'Gj', 9: 'Cal', 10: 'kCal', 11: 'Mcal', 12: 'Gcal', 13: 'varh',
    14: 'kvarh', 15: 'Mvarh', 16: 'Gvarh', 17: 'VAh', 18: 'kVAh',
    19: 'MVAh', 20: 'GVAh', 21: 'kW', 22: 'kW', 23: 'MW', 24: 'GW',
    25: 'kvar', 26: 'kvar', 27: 'Mvar', 28: 'Gvar', 29: 'VA', 30: 'kVA',
    31: 'MVA', 32: 'GVA', 33: 'V', 34: 'A', 35: 'kV',36: 'kA', 37: 'C',
    38: 'K', 39: 'l', 40: 'm3', 41: 'l/h', 42: 'm3/h', 43: 'm3xC',
    44: 'ton', 45: 'ton/h', 46: 'h', 47: 'hh:mm:ss', 48: 'yy:mm:dd',
    49: 'yyyy:mm:dd', 50: 'mm:dd', 51: '', 52: 'bar', 53: 'RTC',
    54: 'ASCII', 55: 'm3 x 10', 56: 'ton x 10', 57: 'GJ x 10',
    58: 'minutes', 59: 'Bitfield', 60: 's', 61: 'ms', 62: 'days',
    63: 'RTC-Q', 64: 'Datetime'
}

#######################################################################
# Kamstrup uses the "true" CCITT CRC-16
#

def crc_1021(message):
        poly = 0x1021
        reg = 0x0000
        for byte in message:
                mask = 0x80
                while(mask > 0):
                        reg<<=1
                        if byte & mask:
                                reg |= 1
                        mask>>=1
                        if reg & 0x10000:
                                reg &= 0xffff
                                reg ^= poly
        return reg

#######################################################################
# Byte values which must be escaped before transmission
#

escapes = {
    0x06: True,
    0x0d: True,
    0x1b: True,
    0x40: True,
    0x80: True,
}

#######################################################################
# And here we go....
#
class kamstrup(object):

    def __init__(self, serial_port = "/dev/cuaU0"):
        self.debug_fd = open("_kamstrup", "a")
        self.debug_fd.write("\n\nStart\n")
        self.debug_id = None

        self.ser = serial.Serial(
            port = serial_port,
            baudrate = 9600,
            timeout = 1.0)

    def debug(self, dir, b):
        for i in b:
            if dir != self.debug_id:
                if self.debug_id != None:
                    self.debug_fd.write("\n")
                self.debug_fd.write(dir + "\t")
                self.debug_id = dir
            self.debug_fd.write(" %02x " % i)
        self.debug_fd.flush()

    def debug_msg(self, msg):
        if self.debug_id != None:
            self.debug_fd.write("\n")
        self.debug_id = "Msg"
        self.debug_fd.write("Msg\t" + msg)
        self.debug_fd.flush()

    def wr(self, b):
        b = bytearray(b)
        self.debug("Wr", b);
        print('Send: ', [hex(bi) for bi in b])
        self.ser.write(b)

    def rd(self):
        a = self.ser.read(1)
        if len(a) == 0:
            self.debug_msg("Rx Timeout")
            return None
        b = bytearray(a)[0]
        self.debug("Rd", bytearray((b,)));
        return b
    def rd_all(self,):
        a = self.ser.readline()
        if len(a) == 0:
            self.debug_msg("Rx Timeout")
            return None
        b = bytearray(a)
        return b

    def send(self, pfx, msg):
        b = bytearray(msg)

        b.append(0)
        b.append(0)
        c = crc_1021(b)
        b[-2] = c >> 8
        b[-1] = c & 0xff

        c = bytearray()
        c.append(pfx)
        for i in b:
            if i in escapes:
                c.append(0x1b)
                c.append(i ^ 0xff)
            else:
                c.append(i)
        c.append(0x0d)
        self.wr(c)

    def recv(self):
        b = bytearray()
        #d_all = self.ser.readline()
        #print('d_all: ', d_all)
        #print('d_all: ', [bi for bi in d_all])
        #print('d_all: ', [ord(bi) for bi in d_all])
        while True:
            d = self.rd()
            if d == None:
                return None
            elif d == 0x40:
                b = bytearray()
            b.append(d)
            if d == 0x0d:
                break
        #b = self.rd_all()
        print('b: ', [hex(bi) for bi in b])
        c = bytearray()
        i = 1;
        while i < len(b) - 1:
            if b[i] == 0x1b:
                v = b[i + 1] ^ 0xff
                if v not in escapes:
                    self.debug_msg(
                        "Missing Escape %02x" % v)
                c.append(v)
                i += 2
            else:
                c.append(b[i])
                i += 1
        #print('c: ', [hex(ci) for ci in c])
        if crc_1021(c):
            self.debug_msg("CRC error")
            print("CRC error")
        #print('recv: ', [hex(ci) for ci in c[:-2]])
        return c[:-2]

    def readvar(self, nbr):
        # I wouldn't be surprised if you can ask for more than
        # one variable at the time, given that the length is
        # encoded in the response.  Havn't tried.
        

        #self.send(0x80, (0x3f, 0x10, 0x01, nbr >> 8, nbr & 0xff))
        self.send(0x0e, (0x3f, 0x10, 0x01, nbr >> 8, nbr & 0xff))

        b = self.recv()
        b_hex = [hex(bi) for bi in b]
        #print('b: ', b_hex)
        if b_hex == ['0x3f', '0x10', '0x1', '0x0', hex(nbr)]:
            print('No connection to instruments')
            return (None, None)
        print('nbr: ', nbr)
        print('b_hex: ', b_hex)
        if b == None:
            print('case 1')
            return (None, None)
        elif b[0] != 0x3f or b[1] != 0x10:
            print('case 2')
            return (None, None)
        elif b[2] != nbr >> 8 or b[3] != nbr & 0xff:
            print('case 3')
            #return (None, None)
        if b[4] in units:
            u = units[b[4]]
        else:
            u = None
        print('unit: ', u)

        # Decode the mantissa
        x = 0
        for i in range(0,b[5]):
            x <<= 8
            x |= b[i + 7]

        # Decode the exponent
        i = b[6] & 0x3f
        if b[6] & 0x40:
            i = -i
        i = math.pow(10,i)
        if b[6] & 0x80:
            i = -i
        x *= i

        if False:
            # Debug print
            s = ""
            for i in b[:4]:
                s += " %02x" % i
            s += " |"
            for i in b[4:7]:
                s += " %02x" % i
            s += " |"
            for i in b[7:]:
                s += " %02x" % i

            print(s, "=", x, units[b[4]])

        return (x, u)
            
            
def test():
    test_string = [0x80, 0x3f, 0x01, 0x05, 0x8a,]
    ser = serial.Serial(
            port = '/dev/serial/by-id/usb-Silicon_Labs_Kamstrup_M-Bus_Master_MultiPort_250D_131751521-if00-port0',
            baudrate = 2400,#38400,
            timeout = 1.0)
    print('com: ', test_string)
    ser.write(bytearray(test_string))
    line = ser.readlines()
    print('res: ', [ord(b) for b in line])

if __name__ == "__main__":
    import time
    #import serial
    #serial_port = '/dev/serial/by-id/usb-Silicon_Labs_Kamstrup_USB_interface_0001-if00-port0'
    #ser = serial.Serial(
    #        port = serial_port,
    #        baudrate = 300,
    #        timeout = 1.0)
    #ser.write("/?!\n")
    #line = ser.readline()
    #print('res: ', line)
    #ser.close()
    #foo = kamstrup(serial_port = '/dev/serial/by-id/usb-Silicon_Labs_Kamstrup_M-Bus_Master_MultiPort_250D_131751521-if00-port0')
    #foo = kamstrup(serial_port = '/dev/ttyUSB0')
    #for i in kamstrup_382_var:
    #    print(foo.readvar(i))
        #print("%-25s" % kamstrup_382_var[i], x, u)
    #for key, value in kamstrup_302_var.items():
    #for value in [60,  ]:
    #    x,u = foo.readvar(value)
    #    print("%-25s" % 'unknown', x, u)
    """
    test_string = [[0x0e, 0x3f, 0x10, 0x01, 0x00, 0x01, 0x55, 0xa1, 0x0d], 
                   [0x80, 0x3f, 0x01, 0x05, 0x8a, 0x0d],
                   [0x80, 0x3f, 0x10, 0x01, 0x03, 0xe9, 0x7c, 0xd4, 0x0d],
                   [0x80, 0x3f, 0x62, 0x04, 0x00, 0x01, 0x01, 0x01, 0x03, 0xeb, 0x5d, 0x4d, 0x0d],
                   [0x80, 0x3f, 0x62, 0x04, 0x00, 0x01, 0x01, 0x01, 0x03, 0xea, 0x4d, 0x6c, 0x0d],
                   [0x80, 0x3f, 0x62, 0x04, 0x00, 0x01, 0x01, 0x01, 0x00, 0x3f, 0x83, 0xe7, 0x0d]]
    test_string2 = [[0x80, 0x3f, 0x01, 0x05, 0x8a, 0x0d], 
                   [0x80, 0x3f, 0x01, 0x05, 0x8a, 0x0d],
                   [0x80, 0x3f, 0x10, 0x01, 0x03, 0xe9, 0x7c, 0xd4, 0x0d],
                   [0x80, 0x3f, 0x62, 0x04, 0x00, 0x01, 0x01, 0x01, 0x03, 0xeb, 0x5d, 0x4d, 0x0d],
                   [0x80, 0x3f, 0x62, 0x04, 0x00, 0x01, 0x01, 0x01, 0x03, 0xea, 0x4d, 0x6c, 0x0d],
                   [0x80, 0x3f, 0x62, 0x04, 0x00, 0x01, 0x01, 0x01, 0x00, 0x3f, 0x83, 0xe7, 0x0d]]
    ser = serial.Serial(
            port = '/dev/serial/by-id/usb-Silicon_Labs_Kamstrup_M-Bus_Master_MultiPort_250D_131751521-if00-port0',
            baudrate = 2400,#38400,
            timeout = 1.0)
    for i in range(4):
        print('com: ', test_string[i])
        ser.write(bytearray(test_string[i]))
        line = ser.readlines()
        print('res: ', [ord(b) for b in line])
        
    """
    test()