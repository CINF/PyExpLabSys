# pylint: disable=R0913,W0142,C0103

""" Temperature controller """
import time
import threading
import socket
import curses

import PyExpLabSys.drivers.cpx400dp as CPX
import PyExpLabSys.aux.pid as PID


class CursesTui(threading.Thread):
    """ Text user interface for Volvo heating controll """
    def __init__(self, heating_class):
        threading.Thread.__init__(self)
        self.quit = False
        self.hc = heating_class
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)

    def run(self):
        while not self.quit:
            self.screen.addstr(3, 2, 'Running')
            self.screen.addstr(4, 2, "Heating voltage: {0:.2f}V      ".format(self.hc.voltage))
            self.screen.addstr(5, 2, "Heating current: {0:.2f}A      ".format(self.hc.current))
            self.screen.addstr(6, 2, "Heating power: {0:.2f}W        ".format(self.hc.heatingpower()))
            self.screen.addstr(7, 2, "Filament resisance: {0:.2f}Ohm      ".format(self.hc.resistance()))

            self.screen.addstr(9, 40, "Setpoint: {0:.2f}C       ".format(self.hc.pc.setpoint))
            self.screen.addstr(9, 2, "Temeperature: {0:.3f}C       ".format(self.hc.pc.temperature))

            n = self.screen.getch()
            if n == ord('q'):
                self.hc.quit = True
                self.quit = True
            if n == ord('i'):
                self.hc.setpoint = self.hc.pc.update_setpoint(self.hc.pc.setpoint + 1)
            if n == ord('d'):
                self.hc.setpoint = self.hc.pc.update_setpoint(self.hc.pc.setpoint - 1)

            self.screen.refresh()
            time.sleep(0.2)
        self.stop()

    def stop(self):
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()  


class PowerCalculatorClass(threading.Thread):
    """ Calculate the wanted amount of power """
    def __init__(self):
        threading.Thread.__init__(self)
        self.power = 0
        self.setpoint = 40
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
            #self.pid.UpdateSetpoint(self.setpoint)
            time.sleep(0.25)


class HeaterClass(threading.Thread):
    """ Do the actual heating """
    def __init__(self, power_calculator):
        threading.Thread.__init__(self)
        self.pc = power_calculator
        self.heater = CPX.CPX400DPDriver(2,usbchannel=0)
        self.maxcurrent = 0.5
        self.quit = False
        self.heater.set_voltage(0.3)
        self.heater.output_status(True)
        time.sleep(2)
        self.current = self.heater.read_actual_current()
        self.voltage = self.heater.read_actual_voltage()
        self.heater.output_status(False)
        self.heater.set_voltage(0)
        self.filament_resistance = self.resistance()

    def heatingpower(self):
        """ Calculate the current heating power """
        power = self.current * self.voltage
        return(power)

    def resistance(self):
        """ Calculate resistance of filament """
        if self.current > 0.02:
            resistance = self.voltage / self.current
        else:
            resistance = -1
        return(resistance)

    def run(self):
        self.heater.output_status(True)
        while not self.quit:
            try:
                wanted_voltage = (self.pc.read_power() * self.resistance()) ** 0.5
            except ValueError:
                wanted_voltage = 0
            self.heater.set_voltage(wanted_voltage)
            time.sleep(1)
            self.current = self.heater.read_actual_current()
            self.voltage = self.heater.read_actual_voltage()


P = PowerCalculatorClass()
P.daemon = True
P.start()

H = HeaterClass(P)
#H.daemon = True
H.start()

T = CursesTui(H)
#T.daemon = True
T.start()
