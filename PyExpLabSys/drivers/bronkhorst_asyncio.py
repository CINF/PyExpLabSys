# -*- coding: utf-8 -*-
""" Asyncio driver for Bronkhorst flow controllers, including simple test case """
from __future__ import print_function
import sys
import serial
import asyncio
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


class Bronkhorst(object):
    """ Driver for Bronkhorst flow controllers """
    def __init__(self, device_name, port, max_flow):
        self.port = port
        self.max_setting = max_flow
        self.device_name = device_name
        
    async def setup(self):
        try:
            self.ser = serial.Serial(self.port, 38400, timeout=2)
            await asyncio.sleep(0.25)
            ser = await self.read_serial()
            if len(ser) < 3:
                raise Exception('MfcNotFound')
        except serial.serialutil.SerialException:
            print('{} port not found {}'.format(self.device_name, self.port))
        except:
            print('{} not found'.format(self.device_name))

    async def comm(self, command):
        """ Send commands to device and recieve reply """
        try:
            self.ser.write(command.encode('ascii'))
            await asyncio.sleep(0.1)
            return_string = self.ser.read(self.ser.inWaiting())
            return_string = return_string.decode()
        except (AttributeError, UnicodeDecodeError):
            print('{} not connected'.format(self.device_name))
            return_string = 'Error'
        return return_string

    async def read_setpoint(self):
        """ Read the current setpoint """
        read_setpoint = ':06800401210121\r\n' # Read setpoint
        response = await self.comm(read_setpoint)
        try:
            response = int(response[11:], 16)
            response = (response / 32000.0) * self.max_setting
        except ValueError:
            response = 'Error'
        return response  
    
    async def read_flow(self):
        """ Read the actual flow """
        read_pressure = ':06800401210120\r\n' # Read pressure
        val = await self.comm(read_pressure)
        try:
            val = val[-6:]
            num = int(val, 16)
            pressure = (1.0 * num / 32000) * self.max_setting
        except ValueError:
            pressure = 'Error'
        return pressure

    async def set_flow(self, setpoint):
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
        response = await self.comm(set_setpoint)
        response_check = response[5:].strip()
        if response_check == '000005':
            response = 'ok'
        else:
            response = 'Error'
        return response

    async def read_counter_value(self):
        """ Read valve counter. Not fully implemented """
        read_counter = ':06030401210141\r\n'
        response = await self.comm(read_counter)
        return str(response)

    async def set_control_mode(self):
        """ Set the control mode to accept rs232 setpoint """
        set_control = ':058001010412\r\n'
        response = await self.comm(set_control)
        return str(response)

    async def read_serial(self):
        """ Read the serial number of device """
        read_serial = ':1A8004F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        error = 0
        while error < 10:
            response = await self.comm(read_serial)
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

    async def read_unit(self):
        """ Read the flow unit """
        read_capacity = ':1A8004F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        response = await self.comm(read_capacity)
        response = response[77:-26]
        try:
            response = bytes.fromhex(response).decode('utf-8')
        except AttributeError: # Python2
            response = response.decode('hex')

        return str(response)

    async def read_capacity(self):
        """ Read ?? from device """
        read_capacity = ':1A8004F1EC7163006D71660001AE0120CF014DF0017F077101710A\r\n'
        response = await self.comm(read_capacity)
        response = response[65:-44]
        #response = response.decode('hex')
        return str(response)
