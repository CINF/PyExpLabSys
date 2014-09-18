# pylint: disable=C0301,R0904, R0902, C0103

import time
import threading
import curses
import PyExpLabSys.drivers.cpx400dp as CPX
import PyExpLabSys.aux.pid as pid
from PyExpLabSys.common.sockets import DateDataSocket
#from PyExpLabSys.common.loggers import ContinuousLogger
#from PyExpLabSys.common.sockets import LiveSocket
from ABElectronics_DeltaSigmaPi import DeltaSigma


class CursesTui(threading.Thread):
    """ Text gui for emission control """
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
            self.screen.addstr(5, 2, "Filament voltage: {0:.2f}V     ".format(self.eci.filament['voltage']))
            self.screen.addstr(6, 2, "Filament current: {0:.2f}A    ".format(self.eci.filament['current']))
            if self.eci.filament['current'] > 0.01:
                self.screen.addstr(5, 40, "Filament resisance: {0:.2f}Ohm      ".format(self.eci.filament['voltage'] / self.eci.filament['current']))
            else:
                self.screen.addstr(5, 40, "Filament resisance: -                   ")
            self.screen.addstr(6, 40, "Filament power: {0:.2f}W      ".format(self.eci.filament['voltage'] * self.eci.filament['current']))
            self.screen.addstr(8, 2, "Grid Voltage: {0:.2f}V       ".format(self.eci.bias['grid_voltage']))
            self.screen.addstr(8, 40, "Grid Current: {0:.3f}A       ".format(self.eci.bias['grid_current']))
            self.screen.addstr(12, 2, "Emission current: {0:.4f}mA    ".format(self.eci.emission_current))
            self.screen.addstr(12, 40, "Setpoint: {0:.2f}mA".format(self.eci.setpoint))
            self.screen.addstr(13, 2, "Measured voltage: {0:.4f}mV    ".format(self.eci.measured_voltage * 1000))
            try:
                self.screen.addstr(14, 2, "Update rate: {0:.1f}Hz    ".format(1/self.eci.looptime))
            except ZeroDivisionError:
                pass

            n = self.screen.getch()
            if n == ord('q'):
                self.eci.running = False
            if n == ord('i'):
                self.eci.setpoint = self.eci.update_setpoint(self.eci.setpoint + 0.1)
            if n == ord('d'):
                self.eci.setpoint = self.eci.update_setpoint(self.eci.setpoint - 0.1)

            self.screen.refresh()
            time.sleep(0.2)

    def stop(self):
        """ Reset the terminal """
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()


class EmissionControl(threading.Thread):
    """ Control the emission of a filament. """
    def __init__(self, datasocket=None):
        threading.Thread.__init__(self)
        if datasocket is not None:
            self.datasocket = datasocket
        else:
            self.datasocket = None    
        self.measured_voltage = 0
        self.filament = {}
        self.filament['device'] = CPX.CPX400DPDriver(1, usbchannel=0)
        self.filament['voltage'] = 0
        self.filament['current'] = 0
        self.filament['idle_voltage'] = 3
        self.filament['device'].set_current_limit(5)
        self.filament['device'].output_status(True)
        self.bias = {}
        self.bias['device'] = CPX.CPX400DPDriver(2, usbchannel=0)
        self.bias['grid_voltage'] = 0
        self.bias['grid_current'] = 0
        self.bias['device'].output_status(True)
        self.looptime = 0
        self.update_setpoint(0.2)
        self.adc = DeltaSigma(0x68, 0x69, 18)
        self.adc.setPGA(8)  # Adjust this if resistor value is changed
        self.running = True
        self.wanted_voltage = 0
        self.emission_current = 999
        self.pid = pid.PID(2, 0.07, 0, 9)
        self.pid.UpdateSetpoint(self.setpoint)

    def set_bias(self, bias):
        """ Set the bias-voltage """
        if bias > -1:
            self.bias['device'].set_voltage(bias)
        if bias < 5:
            pass  # TODO: Implement check to make sure not to melt the filament

    def update_setpoint(self, setpoint):
        """ Update the setpoint """
        self.setpoint = setpoint
        if self.datasocket is not None:
            self.datasocket.set_point_now('setpoint', setpoint)

    def set_filament_voltage(self, U):
        """ Set the filament voltage """
        return(self.filament['device'].set_voltage(U))

    def read_filament_voltage(self):
        """ Read the filament voltage """
        return(self.filament['device'].read_actual_voltage())

    def read_filament_current(self):
        """ Read the filament current """
        return(self.filament['device'].read_actual_current())

    def read_grid_voltage(self):
        """Read the actual grid voltage """
        return(self.bias['device'].read_actual_voltage())

    def read_grid_current(self):
        """ Read the grid current as measured by power supply """
        return(self.bias['device'].read_actual_current())

    def read_emission_current(self):
        """ Read the actual emission current """
        value = self.adc.readVoltage(1)
        self.measured_voltage = value
        current = 1000.0 * value / 3.4  # Resistance value read off component label
        return(current)

    def run(self):
        while self.running:
            #time.sleep(0.1)
            t = time.time()
            self.emission_current = self.read_emission_current()
            self.wanted_voltage = self.pid.WantedPower(self.emission_current) + self.filament['idle_voltage']
            self.pid.UpdateSetpoint(self.setpoint)
            self.set_filament_voltage(self.wanted_voltage)
            self.filament['voltage'] = self.read_filament_voltage()
            self.filament['current'] = self.read_filament_current()
            self.bias['grid_voltage'] = self.read_grid_voltage()
            self.bias['grid_current'] = self.read_grid_current()
            if self.datasocket is not None:
                self.datasocket.set_point_now('emission', self.emission_current)
            self.looptime = time.time() - t
        self.setpoint = 0
        self.set_filament_voltage(0)
        self.set_bias(0)


if __name__ == '__main__':

    datasocket = DateDataSocket(['setpoint', 'emission'], timeouts=[999999, 1.0])
    datasocket.start()

    ec = EmissionControl(datasocket)
    ec.set_bias(40)
    ec.start()

    tui = CursesTui(ec)
    tui.daemon = True
    tui.start()
