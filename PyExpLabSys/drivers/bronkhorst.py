""" Driver for Bronkhorst flow controllers, including simple test case """
from __future__ import print_function
import time
import sys
import serial
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


class Bronkhorst(object):
    """ Driver for Bronkhorst flow controllers """
    def __init__(self, port, max_flow, node_channel=None, serial=None):
        #Check for default serial for back compadibility
        if serial is None:
            self.ser = serial.Serial(port, 38400, timeout=2)
        else:
            self.ser = serial
            
        self.max_setting = max_flow

        #Check for default node_channel for back compadibility
        if node_channel is None:
            self.node = 80
        else :
            self.node = node_channel #In hex
            
        if len(serial) < 3:
            raise Exception('MfcNotFound')


    def comm(self, command):
        """ Send commands to device and recieve reply """
        self.ser.write(command.encode('ascii'))
        time.sleep(0.1)
    
        return_string = self.ser.read(self.ser.inWaiting())
        return_string = return_string.decode()
        return return_string



    def read_setpoint(self):
        """ Read the current setpoint """
        read_setpoint = ':06' + self.node + '0401210121\r\n' # Read setpoint
        response = self.comm(read_setpoint)
        response = int(response[11:], 16) #Grabs last 4 hex numbers and converts to decimal
        response = (float(response) / 32000.0) * float(self.max_setting) #response / 32000 gives percentage, then multiply by max setting
        return response



    def read_flow(self):
        """ Read the actual flow """ #If 10 errors then returns 99
        error = 0
        while error < 10:
            read_pressure = ':06' + self.node + '0401210120\r\n' # Read pressure
            val = self.comm(read_pressure)

            try:
                val = val[11:] #Gets last 4 hex digits
                num = int(val, 16) #Converts to decimal
                pressure = (float(num)/ 32000) * float(self.max_setting) #Determines actual flow
                break

            except ValueError:
                pressure = -99
                error = error + 1
        
        return pressure


    def set_flow(self, setpoint):
        
        """ Set the desired setpoint, which could be a pressure """
        if setpoint > 0:
            setpoint = (float(setpoint) / float(self.max_setting)) * 32000
            setpoint = hex(int(setpoint))
            setpoint = setpoint.upper()
            setpoint = setpoint[2:].rstrip('L')

            if len(setpoint) == 3:
                setpoint = '0' + setpoint

        else:
            setpoint = '0000'
        
        set_setpoint = ':06' + self.node + '010121' + setpoint + '\r\n' # Set setpoint
        response = self.comm(set_setpoint)
        response_check = response[5:].strip()
        
        if response_check == '000005':
            response = 'ok'
        else:
            response = 'error'
        
        return response



    def read_counter_value(self):
        """ Read valve counter. Not fully implemented """
        read_counter = ':06030401210141\r\n'
        response = self.comm(read_counter)
        return str(response)

    def set_control_mode(self):
        """ Set the control mode to accept rs232 setpoint """
        set_control = ':05' + self.node + '01010412\r\n' #Sets control mode to value 18 (rs232)
        response = self.comm(set_control)
        return str(response)


    def read_serial(self):
        """ Read the serial number of device """        
        read_serial = ':1A' + self.node + '04F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        error = 0
        while error < 10:
            response = self.comm(read_serial)
            response = response[13:-84]
            if sys.version_info[0] < 3: # Python2
                try:
                    response = response.decode('hex')
                except TypeError:
                    response = ''
            else: # Python 3
                try:
                    response = bytes.fromhex(response).decode('utf-8')
                except ValueError:
                    response = ''

            if response == '':
                error = error + 1
            else:
                error = 10

        return str(response)


    def read_unit(self):
        """ Read the flow unit """
        read_capacity = ':1A' + self.node + '04F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        response = self.comm(read_capacity)
        response = response[77:-26]
        
        try:
            response = bytes.fromhex(response).decode('utf-8')
        except AttributeError: # Python2
            response = response.decode('hex')

        return str(response)


    def read_capacity(self):
        """ Read ?? from device (Not implemented)"""
        read_capacity = ':1A' + self.node + '04F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        response = self.comm(read_capacity)
        response = response[65:-44]
        #response = response.decode('hex')
        return str(response)


if __name__ == '__main__':
    ser1 = serial.Serial('/dev/ttyUSB3', 38400, timeout=2)
    ser2 = serial.Serial('/dev/COM3', 38400, timeout=2)
    bh_arr = []
    bh_arr.append(Bronkhorst(None, 100, hex(10), ser1))
    bh_arr.append(Bronkhorst(None, 100, hex(20), ser1))
    bh_arr.append(Bronkhorst(None, 100, hex(30), ser1))
    bh_arr.append(Bronkhorst(None, 100, hex(40), ser2))
    #print bh.set_setpoint(1.0)
    #time.sleep(1)
    for bh in bh_arr:
        print(bh.read_serial())
        print(bh.read_flow())
        print(bh.read_unit())
        print(bh.read_capacity())
        print(bh.read_counter_value())
