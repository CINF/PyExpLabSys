# -*- coding: utf-8 -*-
"""
Created on Wed Jul 29 13:58:31 2020

@author: asmos (you can ask thoe for questions)
"""
import sys
from smbus import SMBus
import time
import RPi.GPIO

try:
    bus = SMBus(1)
except:
    raise OSError('No connection to I2C bus')    

def i2c_communicate(address, flowA_setpoint, flowB_setpoint, flowC_setpoint, flowD_setpoint, flowE_setpoint, ttl=0xFF, sleeptime=0.05, echo=False):
    try:
        result = bus.read_i2c_block_data(address, 0, 24)
        time.sleep(sleeptime)
        if echo:
            print("Device at address %s (%i) responded with"%(hex(address), address))
            for register, data in enumerate(result):
                print('%s: %s' %(register, hex(data)))
            print('\n\n')
        if result[21] != ttl:
            bus.write_i2c_block_data(address, 0x15, [ttl, 0x15])
        time.sleep(sleeptime)
        bus.write_i2c_block_data(address, 0x10, [flowA_setpoint, flowB_setpoint, flowC_setpoint, flowD_setpoint, flowE_setpoint])
        time.sleep(sleeptime)
    except:
        print('No connection to device %s'%(hex(address)))
        result = None

    if result is not None:
        _raw_flowA = (0b00000011 & result[1])*256+result[2]
        _raw_flowB = (0b00000011 & result[4])*256+result[5]
        _raw_flowC = (0b00000011 & result[7])*256+result[8]
        _raw_flowD = (0b00000011 & result[10])*256+result[11]
        _raw_flowE = (0b00000011 & result[13])*256+result[14]

        return _raw_flowA, _raw_flowB, _raw_flowC, _raw_flowD, _raw_flowE
    else:
        return -1000, -1000, -1000, -1000, -1000

def pressure_control(pressure_setpoint, echo=False):
    if pressure_setpoint < 0.25:
        setpoint = 0.25
    #setpoint = round(((pressure_setpoint-0.2112)/0.0328)*255/1023) #old calibration
    setpoint = round(((pressure_setpoint-0.2449)/0.0329)*255/1023) #old calibration
    dat = i2c_communicate(0x16, setpoint, 0, 0, 0, 0, echo=echo)
    return round(dat[0]*0.0329+0.2449,2)
    #return round(0.0328*dat[0]+0.2112,2) #old calibration

def loading_animation(loading_time):
    loading_animation = ['/','|','\\','-']
    cache_time = time.time()
    n = 0
    j=1
    while time.time()-cache_time < loading_time:
        time.sleep(0.2)
        print(j*loading_animation[n], end='\r')
        n=n+1
        if n == 4:
            n=0
            j=j+1

def MFC_setpoint_1volt_shift(setpoint): #number between 0 and 255
    corrected_setpoint = ((setpoint*(255-54)/255))+54
    #corrected_setpoint = ((setpoint*(1023-219)/255)+219)
    return corrected_setpoint

def MFC_data_1volt_shift(data): #shift is 219, full range is 1023
    corrected_data = (data-219)*1023/(1023-219)
    if corrected_data < 0:
        corrected_data = 0
    return corrected_data

class Relay():
    global bus

    def __init__(self):
        self.DEVICE_ADDRESS = 0x20
        self.DEVICE_REG_MODE1 = 0x06
        self.DEVICE_REG_DATA = 0xff
        bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)

    def ON_1(self):
        self.DEVICE_REG_DATA &= ~(0x1 <<0)
        bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)

    def ON_2(self):
        self.DEVICE_REG_DATA &= ~(0x1 << 1)
        bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)

    def ON_3(self):
        self.DEVICE_REG_DATA &= ~(0x1 << 2)
        bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)

    def ON_4(self):
        self.DEVICE_REG_DATA &= ~(0x1 << 3)
        bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)

    def OFF_1(self):
        self.DEVICE_REG_DATA |= (0x1 << 0)
        bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)

    def OFF_2(self):
        self.DEVICE_REG_DATA |= (0x1 << 1)
        bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)

    def OFF_3(self):
        self.DEVICE_REG_DATA |= (0x1 << 2)
        bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)

    def OFF_4(self):
        self.DEVICE_REG_DATA |= (0x1 << 3)
        bus.write_byte_data(self.DEVICE_ADDRESS, self.DEVICE_REG_MODE1, self.DEVICE_REG_DATA)
    
    def MFC_powersupply_ON(self):
        self.ON_2()
        self.ON_3()
        self.ON_4()
        
    def MFC_powersupply_OFF(self):
        self.OFF_2()
        self.OFF_3()
        self.OFF_4()

class arduino():

    def __init__(self):
        self.gpio = RPi.GPIO
        self.gpio.setmode(self.gpio.BCM)
        self.gpio.mode = self.gpio.getmode()
        self.gpio.setup(25, self.gpio.OUT)
        self.gpio.output(25,1)
        self.gpio.setup(24, self.gpio.OUT)
        self.gpio.output(24,1)

    def reset_arduino(self):
        self.gpio.output(25,0)
        time.sleep(0.1)
        self.gpio.output(25,1)
        
    def reset_pres_arduino(self):
        self.gpio.output(24,0)
        time.sleep(0.1)
        self.gpio.output(24,1)    

if __name__ == "__main__":
    address = 0x16
    flowA_setpoint = 0 #brun
    flowB_setpoint = 0 #rød
    flowC_setpoint = 0 #grøn
    flowD_setpoint = 0 #blå
    flowE_setpoint = 0 #grå
    while True:
        dat = i2c_communicate(address, flowA_setpoint, flowB_setpoint, flowC_setpoint, flowD_setpoint, flowE_setpoint, echo=False)
        #print(dat)
        time.sleep(0.5)
        print(dat[0])

if __name__ == "__main__":
    pressure_setpoint = 0
    while True:
        dat = pressure_control(pressure_setpoint)
        print(dat)
        time.sleep(0.5)
