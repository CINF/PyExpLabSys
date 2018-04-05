""" Driver for Bronkhorst flow controllers, including simple test case """
from __future__ import print_function
import time
import sys
import serial
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


class Bronkhorst(object):
    """ Driver for Bronkhorst flow controllers """
    def __init__(self, port, max_flow):
        self.ser = serial.Serial(port, 38400, timeout=2)
        self.max_setting = max_flow
        time.sleep(0.25)
        ser = self.read_serial()
        if len(ser) < 3:
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
        read_setpoint = ':06800401210121\r\n' # Read setpoint
        response = self.comm(read_setpoint)
        response = int(response[11:], 16)
        response = (response / 32000.0) * self.max_setting
        return response

    def read_flow(self):
        """ Read the actual flow """
        error = 0
        while error < 10:
            read_pressure = ':06800401210120\r\n' # Read pressure
            val = self.comm(read_pressure)
            try:
                val = val[-6:]
                num = int(val, 16)
                pressure = (1.0 * num / 32000) * self.max_setting
                break
            except ValueError:
                pressure = -99
                error = error + 1
        return pressure

    def set_flow(self, setpoint):
        """ Set the desired setpoint, which could be a pressure """
        setpoint = float(setpoint)
        if setpoint > 0:
            setpoint = (1.0 * setpoint / self.max_setting) * 32000
            setpoint = hex(int(setpoint))
            setpoint = setpoint.upper()
            setpoint = setpoint[2:].rstrip('L')
            if len(setpoint) == 3:
                setpoint = '0' + setpoint
        else:
            setpoint = '0000'
        set_setpoint = ':0680010121' + setpoint + '\r\n' # Set setpoint
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
        set_control = ':058001010412\r\n'
        response = self.comm(set_control)
        return str(response)

    def read_serial(self):
        """ Read the serial number of device """
        read_serial = ':1A8004F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
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
        read_capacity = ':1A8004F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        response = self.comm(read_capacity)
        response = response[77:-26]
        try:
            response = bytes.fromhex(response).decode('utf-8')
        except AttributeError: # Python2
            response = response.decode('hex')

        return str(response)

    def read_capacity(self):
        """ Read ?? from device """
        read_capacity = ':1A8004F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        response = self.comm(read_capacity)
        response = response[65:-44]
        #response = response.decode('hex')
        return str(response)


if __name__ == '__main__':
    bh = Bronkhorst('/dev/ttyUSB3', 5)
    #print bh.set_setpoint(1.0)
    #time.sleep(1)
    print(bh.read_serial())
    print(bh.read_flow())
    print(bh.read_unit())
    print(bh.read_capacity())
    print(bh.read_counter_value())
