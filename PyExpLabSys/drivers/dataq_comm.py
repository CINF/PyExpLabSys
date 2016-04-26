# -*- coding: utf-8 -*-
# !/usr/bin/env python

import serial
import time

class DataQ(object):
    """ driver for the DataQ Instrument """
    def __init__(self, port):
        self.serial = serial.Serial(port)
        #time.sleep(0.1)
        self.slist_counter = 0
	
#There is no check on slist_counter and it can hence be overflowed!

    def comm(self, command):
        """ comm function """
        end_string = chr(13) # carriage return
        self.serial.write(command + end_string)
        time.sleep(0.5)
        return_string = self.serial.read(self.serial.inWaiting())
        print('RES: ' + return_string)
        return return_string

    def dataq(self):
        """ """
        command = 'info 0'
        res = self.comm(command)
        return res

    def deviceName(self):
        """ """
        command = 'info 1'
        res = self.comm(command)
        return res

    def firmware(self):
        """ """
        command = 'info 2'
        res = self.comm(command)
        return res

    def serialNumber(self):
        """ """
        command = 'info 6'
        res = self.comm(command)
        return res

    def startMeasurement(self):
        """ """
        command = 'start'
        res = self.comm(command)
        return res

    def stopMeasurement(self):
        """ """
        command = 'stop'
        res = self.comm(command)
        return res

    def ch1Analog(self):
        """ """
        command = 'slist ' + str(self.slist_counter) + ' x0000'
        self.slist_counter = self.slist_counter + 1
        print command, self.slist_counter
        res = self.comm(command)
        return res

    def ch2Analog(self):
        """ """
        command = 'slist ' + str(self.slist_counter) + ' x0001'
        self.slist_counter = self.slist_counter + 1
        res = self.comm(command)
        return res

    def ch3Analog(self):
        """ """
        command = 'slist ' + str(self.slist_counter) + ' x0002'
        self.slist_counter = self.slist_counter + 1
        res = self.comm(command)
        return res

    def setASCIIMode(self):
        """ change response mode to ACSII"""
        command = 'asc'
        res = self.comm(command)
        return res

    def setFloatMode(self):
        """ change response mode to float"""
        command = 'float'
        res = self.comm(command)
        return res

    def resetSlist(self):
        """ Reseting the s list """
        for i in range(5):
            command = 'slist ' + str(i) + ' 0xffff'
            res = self.comm(command)
        return res
        
    def setMultipleOutput(self, value):
        """ """
        command = 'dout ' + value
        res = self.comm(command)
        return res

    def setSingleOutput(self, ch):
        """ """
        if ch == '0':
            value = '14'
        elif ch == '1':
            value = '13'
        elif ch == '2':
            value = '11'
        elif ch == '3':
            value = '08'
        command = 'dout ' + value
        res = self.comm(command)
        return res
    
    def setOutputs(self, ch0=False, ch1=False, ch2=False, ch3=False):
        """ """
        value = 15 - int(ch0)*2**0 - int(ch1)*2**1 - int(ch2)*2**2 - int(ch3)*2**3
        command = 'dout ' + str(value)
        res = self.comm(command)
        return res
        
if __name__ == '__main__':
    dataq = dataq_comm('/dev/ttyACM0')
#    dataq.dataq()
#    dataq.deviceName()
#    dataq.firmware()
#    dataq.serialNumber()
#    dataq.setASCIIMode()
    dataq.ch1Analog()
    dataq.ch2Analog()
    dataq.ch3Analog()
    dataq.setFloatMode()
    for i in range(1,10):
        dataq.startMeasurement()
    else:
        dataq.stopMeasurement()

