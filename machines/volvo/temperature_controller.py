""" Temperature controller """
import time
import threading
import socket
#import curses

import PyExpLabSys.drivers.cpx400dp as CPX
import PyExpLabSys.aux.pid as PID


class PowerCalculatorClass(threading.Thread):
    """ Calculate the wanted amount of power """
    def __init__(self):
        threading.Thread.__init__(self)
        self.power = 0
        self.setpoint = 50
        self.pid = PID.PID()
        self.pid.UpdateSetpoint(self.setpoint)
        self.quit = False
        self.temperature = None

    def read_power(self):
        """ Return the calculated wanted power """
        return(self.power)

    def update_setpoint(self, setpoint):
        """ Update the setpoint """
        self.setpoint = setpoint
        self.pid.UpdateSetpoint(setpoint)
        return(setpoint)

    def run(self):
        data = 'temperature#raw'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        while not self.quit:
            sock.sendto(data, ('localhost', 9000))
            received = sock.recv(1024)
            self.temperature = float(received[received.find(',') + 1:])
            self.power = self.pid.WantedPower(self.temperature)
            self.pid.UpdateSetpoint(self.setpoint)
            time.sleep(0.25)


class HeaterClass(threading.Thread):
    """ Do the actual heating """
    def __init__(self, power_calculator):
        threading.Thread.__init__(self)
        self.pc = power_calculator
        self.heater = CPX.CPX400DPDriver(1,usbchannel=0)
        self.maxcurrent = 0.5
        self.quit = False
        self.heater.set_voltage(0.5)
        self.heater.output_status(True)
        time.sleep(1)
        self.current = self.heater.read_actual_current()
        self.voltage = self.heater.read_actual_voltage()
        self.heater.output_status(False)
        self.filament_resistance = self.resistance()
        print self.current
        print self.voltage
        print self.filament_resistance
        print '---'

    def heatingpower(self):
        power = self.current * self.voltage
        return(power)

    def resistance(self):
        if self.current > 0.02:
            resistance = self.voltage / self.current
        else:
            resistance = -1
        return(resistance)

    def run(self):
        while not self.quit:
            #print(self.heater.read_output_status())
            self.current = self.heater.read_actual_current()
            self.voltage = self.heater.read_actual_voltage()
            print self.pc.read_power()
            wanted_voltage = (self.pc.read_power() * self.resistance())**0.5
            print 'Calculated voltage: ' + str(wanted_voltage)
            self.heater.set_voltage(wanted_voltage)
            time.sleep(1)

P = PowerCalculatorClass()
P.daemon = True
P.start()

H = HeaterClass(P)
H.daemon = True
H.start()

while True:
    time.sleep(1)
