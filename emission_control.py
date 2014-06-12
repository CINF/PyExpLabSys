import time
import threading
import sys
import curses
import socket

import agilent_34972A as multiplexer
import CPX400DP as CPX
import PID

def network_comm(string):
    host='130.225.87.210'
    port = 9696
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.1)
    sock.sendto(string + "\n", (host, port))
    received = sock.recv(1024)
    return received

class CursesTui(threading.Thread):
    def __init__(self, emission_control_instance):
        threading.Thread.__init__(self)
        self.eci = emission_control_instance
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)

    def run(self):
        while True:
            self.screen.addstr(3, 2, 'Running')
            self.screen.addstr(4, 2, "Calculated voltage: {0:.2f}V      ".format(self.eci.wanted_voltage))
            self.screen.addstr(5, 2, "Filament voltage: {0:.2f}V     ".format(self.eci.filament_voltage))
            self.screen.addstr(6, 2, "Filament current: {0:.2f}A    ".format(self.eci.filament_current))
            if self.eci.filament_current > 0.01:
                self.screen.addstr(5, 40, "Filament resisance: {0:.2f}Ohm      ".format(self.eci.filament_voltage / self.eci.filament_current))
            else:
                self.screen.addstr(5, 40, "Filament resisance: -                   ")
            self.screen.addstr(6, 40, "Filament power: {0:.2f}W      ".format(self.eci.filament_voltage * self.eci.filament_current))


            self.screen.addstr(8, 2, "Grid Voltage: {0:.2f}V       ".format(self.eci.grid_voltage))

            self.screen.addstr(8, 40, "Grid Current: {0:.3f}A       ".format(self.eci.grid_current))


            self.screen.addstr(12, 2, "Emission current: {0:.7f}mA    ".format(self.eci.emission_current))
            self.screen.addstr(12, 40, "Setpoint: {0:.2f}mA".format(self.eci.setpoint))
            n = self.screen.getch()
            if n == ord('q'):
                self.eci.running = False
            if n == ord('i'):
                self.eci.setpoint = self.eci.setpoint + 0.1
            if n == ord('d'):
                self.eci.setpoint = self.eci.setpoint - 0.1

            self.screen.refresh()
            time.sleep(0.2)

    def stop(self):
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()    

class EmissionControl(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.filament = CPX.CPX400DPDriver(1,usbchannel=0)
        self.bias = CPX.CPX400DPDriver(2,usbchannel=0)
        self.mux = multiplexer.Agilent34972ADriver(name='tof-agilent-34972a')
        self.running = True
        self.paused = False
        self.wanted_voltage = 0
        self.filament_voltage = 0
        self.filament_current = 0
        self.grid_voltage = 0
        self.grid_current = 0
        self.setpoint = 0.2
        self.emission_current = 999
        self.pid = PID.PID()
        self.pid.Kp = 1
        self.pid.Ki = 0.1
        self.pid.Kd = 0
        self.pid.Pmax = 9
        self.pid.UpdateSetpoint(self.setpoint)

    def set_bias(self, bias):
        if bias > -1:
            self.bias.SetVoltage(bias)
            network_comm('set_bias ' + str(bias))
        if bias < 5:
            pass #TODO: Implement check to make sure not to melt the filament

    def set_filament_voltage(self, U):
        return self.filament.SetVoltage(U)

    def read_filament_voltage(self):
        return self.filament.ReadActualVoltage()

    def read_filament_current(self):
        return self.filament.ReadActualCurrent()

    def read_grid_voltage(self):
        return self.bias.ReadActualVoltage()

    def read_grid_current(self):
        return self.bias.ReadActualCurrent()

    def read_emission_current(self):
        value = self.mux.read_single_scan()[0]
        current = 1000.0 * value / 9.78 #Resistance measured by device itself
        return -1*current

    def run(self):
        i = 0
        paused = True
        while self.running:
            time.sleep(0.1)
            still_paused = network_comm('aps') == 'True'
            if paused and (not still_paused):
                self.mux.set_scan_list(['115'])
                time.sleep(0.2)

            paused = still_paused
            if paused:
                time.sleep(0.25)
            else:
                self.emission_current = self.read_emission_current()
                voltage = self.pid.WantedPower(self.emission_current)
                self.wanted_voltage = voltage
                self.pid.UpdateSetpoint(self.setpoint)
                self.set_filament_voltage(voltage)
                self.filament_voltage = self.read_filament_voltage()
                self.filament_current = self.read_filament_current()
                self.grid_voltage = self.read_grid_voltage()
                self.grid_current = self.read_grid_current()
        self.setpoint = 0
        self.set_filament_voltage(0)
        self.set_bias(0)




if __name__ == '__main__':

    ec = EmissionControl()
    ec.filament.SetCurrentLimit(5)
    #print ec.filament.ReadCurrentLimit()
    #print ec.bias.ReadCurrentLimit()
    ec.set_bias(40)
    ec.start()

    tui = CursesTui(ec)
    tui.daemon = True
    tui.start()

        
    """
    ec.filament.SetVoltage(0)
    time.sleep(2)
    """

    """
    for i in range(0,30):
        ec.filament.SetVoltage(i/5.0)
        print str(ec.filament.ReadActualVoltage()) + ' ' + str(ec.filament.ReadActualCurrent()) + ': ' + str(ec.read_emission_current())
    """
