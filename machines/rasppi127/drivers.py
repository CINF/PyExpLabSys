from __future__ import print_function # Import print as a function in Python2
import minimalmodbus
from pid import PID
import time
import logging                        # Library for logging data
import serial                         # Library for communication through serial commands
from PyExpLabSys.common.supported_versions import python2_and_3
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.drivers.cpx400dp import CPX400DPDriver

# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

class CN9512(object):

    def __init__(self,address=1, port='/dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0'):
        self.instrument = minimalmodbus.Instrument(port,1,mode='rtu')
        self.instrument.serial.baudrate = 9600
        self.instrument.serial.timeout = 1.0

    def read_temperature(self):
        #Read the temperature from the device
        self.temperature = self.instrument.read_register(0x001c)/10.
        return self.temperature

class Heater(object):

    def __init__(self):
        self.tc = CN9512()

        self.power_supply = {}
        for j in [1,2]:
            self.power_supply[j] = CPX400DPDriver(j,
                                                  interface='serial',
                                                  device='/dev/serial/by-path/platform-3f980000.usb-usb-0:1.4:1.0-port0' #'/dev/ttyUSB0'
                                                  )
            #self.set_dual_output()
            self.power_supply[j].set_voltage(0)
            self.power_supply[j].set_current_limit(3.7) #the ATS 3210 Furnace takes 7.28 amps at 240V. At 120V the max current will be below 3.64
            self.power_supply[j].output_status(True)

        self.pid = PID(pid_p=3.,
                       pid_i=0.004,
                       p_max=120,
                       p_min=0
                       )
        
        self.current()
        self.voltage()

    def temperature(self):
        return self.tc.read_temperature()
        
    def setpoint(self):
        return self.pid.setpoint
    
    def update_setpoint(self, setpoint):
        if setpoint != self.pid.setpoint:
            if setpoint < self.pid.setpoint:
                return self.pid.update_setpoint(setpoint) 
            elif setpoint-self.pid.setpoint < 15:
                self.pid.int_err = self.pid.int_err*(15+self.pid.setpoint-setpoint)/15 
                return self.pid.update_setpoint(setpoint)
            else:
                self.pid.reset_int_error()
                return self.pid.update_setpoint(setpoint)
        else:
            return self.pid.setpoint
        
    def heat_ramp(self):
        pass
    
    def current(self):
        return round(self.power_supply[1].read_actual_current(),2)
        
    def voltage(self):
        return round(self.power_supply[1].read_actual_voltage()+self.power_supply[2].read_actual_voltage(),2)
        
    def set_voltage(self, value):
        if value > 120 or value < 0:
            raise ValueError('Voltage should be between 0 and 180.')
            return False
        split_voltage = value/2
        for j in [1,2]:
            self.power_supply[j].set_voltage(split_voltage)
        return value
    
    def heat(self):
        wanted_power = round(self.pid.wanted_power(self.temperature()),2)
        self.set_voltage(round(wanted_power,2))
        return self.voltage, self.current
        #self.set_voltage(wanted_power)

class VPM5(object): #Driver for SmartPirani VPM-5
    """ Driver for SmartPirani """
    def __init__(self, port):
        self.ser = serial.Serial(port, 9600, timeout=2)
        time.sleep(0.1)
        
    def comm(self, command):
        """ Implement communication protocol with appropriate pre- and suffixes"""
        prestring = b'@254'
        endstring = b'\\'
        self.ser.write(prestring + command.encode('ascii') + endstring)
        time.sleep(0.3)
        return_string = self.ser.read(self.ser.inWaiting()).decode()
        return return_string
    
    def read_pressure(self):
        """ Read the pressure from the device"""
        command = 'P?'
        error = 1
        while (error > 0) and (error < 10):
            signal = self.comm(command)
            signal = signal[7:-1]
            try:
                value = float(signal)
                error = 0
            except ValueError: # If there is an error in the output set value to -1
                error = error + 1
                value = -1.0
        return value
    
    def read_temperature(self):
        """ Read the temperature from the device"""
        command = 'T?'
        error = 1
        while (error > 0) and (error < 10):
            signal = self.comm(command)
            signal = signal[7:-1]
            try:
                value = float(signal)
                error = 0
            except ValueError: #If there is an error in the output, set value to -1
                error = error + 1
                value = -1.0
        return value
    
    def Qconfig(self):
        """ Read the temperature from the device"""
        command = 'Q!,PIR'
        signal = self.comm(command)
        return signal
        
    def set_comm_speed(self, speed):
        """ Change the baud rate.
            Speed can be either 4800, 9600, 19.000, 38.400, 57.600 or 115.200"""
        command = 'BAUD!' + str(speed)
        signal = self.comm(command)
        signal = signal[7:-1]
        return signal
    
    def set_unit(self, unit):
        """ Set the unit of the return value.
            unit can be either PASCAL, P,MBAR or P,TORR""" 
        command = "U!" + unit
        signal = self.comm(command)
        signal = signal[7:-1]
        return signal
        
    def read_serial(self):
        """ Read the serial number of the device """
        command = "SN?"
        signal = self.comm(command)
        signal = signal[7:-1]
        return signal

if __name__ == '__main__':
    heater = Heater()
    print(heater.power_supply[1].read_software_version())
    heater.update_setpoint(-9999)
    try:
        while True:
            print(heater.temperature())
            heater.heat()
            time.sleep(1)
    except KeyboardInterrupt:
        heater.update_setpoint(-9999)
        heater.heat()
    #print(str(omega.read_temperature))
