# -*- coding: utf-8 -*-
#!/usr/local/bin/python
from __future__ import print_function


import sys
sys.path.insert(1, '/home/pi/PyExpLabSys')
import time
import logging
from PyExpLabSys.drivers.mbus import MBus 


logging.basicConfig(filename="logger_pykamtest.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

# Value Information Field
VIF = { 0x05: {'subject': 'Energi', 'unit': 'kWh', 'size': 100},
        0x06: {'subject': 'Energi', 'unit': 'kWh', 'size': 1000},
        0x07: {'subject': 'Energi', 'unit': 'kWh', 'size': 10000},
        0x0d: {'subject': 'Energi', 'unit': 'MJ', 'size': 1E5},
        0x0e: {'subject': 'Energi', 'unit': 'GJ', 'size': 1E6},
        0x0f: {'subject': 'Energi', 'unit': 'GJ', 'size': 1E7},

        0x12: {'subject': 'volume', 'unit': 'm3', 'size': 1E-4},
        0x13: {'subject': 'volume', 'unit': 'm3', 'size': 1E-3},
        0x14: {'subject': 'volume', 'unit': 'm3', 'size': 1E-2},
        0x15: {'subject': 'volume', 'unit': 'm3', 'size': 1E-1},
        0x16: {'subject': 'volume', 'unit': 'm3', 'size': 1E-0},

        0x22: {'subject': 'hour counter', 'unit': 'h', 'size': 1},

        0x2b: {'subject': 'power', 'unit': 'kW', 'size': 1E0},
        0x2c: {'subject': 'power', 'unit': 'kW', 'size': 1E1},
        0x2d: {'subject': 'power', 'unit': 'kW', 'size': 1E2},
        0x2e: {'subject': 'power', 'unit': 'MW', 'size': 1E3},
        0x2f: {'subject': 'power', 'unit': 'MW', 'size': 1E4},

        0x3a: {'subject': 'flow', 'unit': 'l/h', 'size': 1E-4},
        0x3b: {'subject': 'flow', 'unit': 'l/h', 'size': 1E-3},
        0x3c: {'subject': 'flow', 'unit': 'm3/h', 'size': 1E-2},
        0x3d: {'subject': 'flow', 'unit': 'm3/h', 'size': 1E-1},
        0x3e: {'subject': 'flow', 'unit': 'm3/h', 'size': 1E-0},

        0x59: {'subject': 'inlet temp', 'unit': 'C', 'size': 1E-2},
        0x5d: {'subject': 'outlet temp', 'unit': 'C', 'size': 1E-2},
        0x61: {'subject': 'diff temp', 'unit': 'K', 'size': 1E-2},

        0x6c: {'subject': 'date', 'unit': 'G-type', 'size': 1},
        0x6d: {'subject': 'date and time', 'unit': 'F-type', 'size': 1},

        0x78: {'subject': 'serial no', 'unit': 'A-type', 'size': 1},
        0x79: {'subject': 'id no', 'unit': 'A-type', 'size': 1},
        0x7a: {'subject': 'address', 'unit': 'C-type', 'size': 1},

        0xff: {'subject': 'unknown', 'unit': 'unknown', 'size': 1},
        }


# Data Information Field    
DIF = { 0x01: {'subject': 'address', 'description': '8 bit binary, Current Value, Type C', 'length': 1, 'DIFE': False, 'fun': lambda X: lambda X: sum([x*256**i for i, x in enumerate(X)])},
        0x0C: {'subject': 'id no', 'description': '8 Digit BCD, Current Value, Type A', 'length': 4, 'DIFE': False, 'fun': lambda X: X},
        0x42: {'subject': 'id no', 'description': '16 Integer, Historical Value, Type G', 'length': 1, 'DIFE': False, 'fun': lambda X: sum([x*256**i for i, x in enumerate(X)])},
        0x4c: {'subject': 'id no', 'description': '32 bit binary, Historical Value, Type B', 'length': 2, 'DIFE': False, 'fun': lambda X: sum([x*256**i for i, x in enumerate(X)])},
        0x44: {'subject': 'id no', 'description': '32 bit binary, Historical Value, Type B', 'length': 2, 'DIFE': False, 'fun': lambda X: sum([x*256**i for i, x in enumerate(X)])},
        0x54: {'subject': 'id no', 'description': '32 bit binary, Maximum, Historical Value, Type B', 'length': 4, 'DIFE': False, 'fun': lambda X: sum([x*256**i for i, x in enumerate(X)])},
        0x84: {'subject': 'id no', 'description': '32 bit binary, Current Value, Type B, DIFE extention follows', 'length': 4, 'DIFE': True, 'fun': lambda X: sum([x*256**i for i, x in enumerate(X)])},
        0xc4: {'subject': 'id no', 'description': '32 bit binary, Historical Value, Type B, DIFE extention follows', 'length': 4, 'DIFE': True, 'fun': lambda X: sum([x*256**i for i, x in enumerate(X)])},
        0x04: {'subject': 'id no', 'description': '32 bit binary, Current Value, Type B', 'length': 4, 'DIFE': False, 'fun': lambda X: sum([x*256**i for i, x in enumerate(X)])},
        
        0x34: {'subject': 'unknown', 'description': 'unknown', 'length': 4, 'DIFE': False, 'fun': lambda X: sum([x*256**i for i, x in enumerate(X)])},
        0x02: {'subject': 'unknown', 'description': 'unknown', 'length': 2, 'DIFE': False, 'fun': lambda X: sum([x*256**i for i, x in enumerate(X)])},
        0x14: {'subject': 'unknown', 'description': 'unknown', 'length': 4, 'DIFE': False, 'fun': lambda X: sum([x*256**i for i, x in enumerate(X)])},
       }


class kamstrup(object):

    def __init__(self, serial_port = "/dev/cuaU0",):
        logging.info('kamstrup class started')
        self.comm = MBus('serial', device=serial_port)
        self.DATA = {}

    def read_data(self, ID = 254):
        self.comm.write_ShortFrame(CF=0x5b, AF=ID)
        userdata = self.comm.read()
        logging.info('MC302, userdata: {}'.format(userdata))
        if userdata != None and len(userdata) > 12:
            data_header = userdata[0:12]
            data = userdata[12:]
        else:
            data = None
        return data
        
    def convert_data(self, userdata):
        if type(userdata) == type(None):
            return None
        n = 0
        #print('DATA out: ', len(userdata))
        while n < len(userdata)-2:# and n < 80:
            remaining = len(userdata[n:])
            n_ori = n
            error = False
            while userdata[n] == 0x00:
                n += 1
            #print(userdata[n:n+7])
            _dif = userdata[n]
            #print('DIF: ', _dif)
            if _dif in DIF:
                #print(DIF[_dif])
                pass
            else:
                #print('error: dif: ', n, _dif)
                logging.warn('setting error : {}  becaurse DIF is not registeres : '.format(True, _dif))
                error = True
            _vif = userdata[n+1]
            if _vif in VIF:
                #print(VIF[_vif])
                pass
            else:
                logging.warn('setting error : {}  becaurse VIF is not registeres : '.format(True, _vif))
                #print('error: vif: ', n, _vif)
                error = True
            if error == False and remaining > 2+DIF[_dif]['length']:
                _values = userdata[n+2:n+2+DIF[_dif]['length']]
                v = DIF[_dif]['fun'](_values) * VIF[_vif]['size']
                #print(v)
                self.DATA[_vif] = {'value': None, 'time': time.time(), 'name':VIF[_vif]['subject']}
                n += 2+DIF[_dif]['length']
                try:
                    self.DATA[_vif]['value'] = float(v)
                    #print(VIF[_vif]['subject'], ' V: ', v)
                except:
                    logging.warn('Cant conver to float {}'.format(v))
                    self.DATA[_vif]['value'] = None    
            else:
                logging.warn('error already exist n: {}'.format(n))
                #print(userdata[n-8:n+8])
                #print('dif: ', _dif, ' vif: ', _vif)
                if _dif in DIF:
                    n += 2+DIF[_dif]['length']
                else:
                    n += 6
            if n_ori == n:
                n += 1
                
        return self.DATA
    
    def read_water_temperature(self,ID):
        raw_data = self.read_data(ID=ID)
        try:
            con_data = self.convert_data(raw_data)
        except:
            logging.warn('failed to convert data from MC302')
        result = {'inlet': None,
                  'outlet': None,
                  'diff': None,
                  'flow': None}
        inlet = None
        outlet = None
        diff = None
        try:
            result['inlet'] = self.DATA[0x59]['value']
            result['outlet'] = self.DATA[0x5d]['value']
            result['diff'] = self.DATA[0x61]['value']
            result['flow'] = self.DATA[0x3b]['value']
        except:
            logging.warn('DATA is is not registered')
            result['inlet'] = None
            result['outlet'] = None
            result['diff'] = None
            result['flow'] = None
        return result
                    
    def run(self,):
        pass
    def close(self):
        self.comm.close()
        

if __name__ == "__main__":
    MC302 = kamstrup(serial_port = '/dev/serial/by-id/usb-Silicon_Labs_Kamstrup_M-Bus_Master_MultiPort_250D_131751521-if00-port0')
    #R = MC302.read_data(ID = 13)
    #d = MC302.convert_data(R)
    for i in range(10):
        print(MC302.read_water_temperature(13)['inlet'])#, MC302.read_water_temperature(14), MC302.read_water_temperature(15))
        print(MC302.read_water_temperature(14)['inlet'])
        print(MC302.read_water_temperature(15)['inlet'])
        time.sleep(2)
    #print(MC302.comm.write_ShortFrame(CF=0x5b, AF=13))
    #alldata = MC302.comm.read()
    #print(alldata)
    #userdata = MC302.read_data(ID=13)
    #print(userdata)
    #D = MC302.convert_data(userdata)
    #print(MC302.DATA[0x59]['value'])
    