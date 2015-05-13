import time
import threading
import curses
import PyExpLabSys.drivers.cpx400dp as CPX
import PyExpLabSys.auxiliary.pid as pid
from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.loggers import ContinuousLogger
#from PyExpLabSys.common.sockets import LiveSocket
from ABE_helpers import ABEHelpers
from ABE_DeltaSigmaPi import DeltaSigma


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
            string = "Calculated voltage: {0:.2f}V      "
            self.screen.addstr(4, 2, string.format(self.eci.wanted_voltage))
            string = "Filament voltage: {0:.2f}V     "
            self.screen.addstr(5, 2, string.format(self.eci.filament['voltage']))
            string = "Filament current: {0:.2f}A    "
            self.screen.addstr(6, 2, string.format(self.eci.filament['current']))
            if self.eci.filament['current'] > 0.01:
                string = "Filament resisance: {0:.2f}Ohm      "
                self.screen.addstr(5, 40, string.format(self.eci.filament['voltage'] /
                                                        self.eci.filament['current']))
            else:
                self.screen.addstr(5, 40, "Filament resisance: -                   ")
            string = "Filament power: {0:.2f}W      "
            self.screen.addstr(6, 40, string.format(self.eci.filament['voltage'] *
                                                    self.eci.filament['current']))
            string = "Grid Voltage: {0:.2f}V       "
            self.screen.addstr(8, 2, string.format(self.eci.bias['grid_voltage']))
            string = "Grid Current: {0:.3f}A       "
            self.screen.addstr(8, 40, string.format(self.eci.bias['grid_current']))
            string = "Emission current: {0:.4f}mA    "
            self.screen.addstr(12, 2, string.format(self.eci.emission_current))
            string = "Setpoint: {0:.2f}mA"
            self.screen.addstr(12, 40, string.format(self.eci.setpoint))
            string = "Measured voltage: {0:.4f}mV    "
            self.screen.addstr(13, 2, string.format(self.eci.measured_voltage * 1000))
            try:
                string = "Update rate: {0:.1f}Hz    "
                self.screen.addstr(14, 2, string.format(1 / self.eci.looptime))
            except ZeroDivisionError:
                pass

            n = self.screen.getch()
            if n == ord('q'):
                self.eci.running = False
            if n == ord('i'):
                #self.eci.setpoint = self.eci.update_setpoint(self.eci.setpoint + 0.1)
                self.eci.setpoint = self.eci.update_setpoint(self.eci.setpoint + 0.1)
            if n == ord('d'):
                #self.eci.setpoint = self.eci.update_setpoint(self.eci.setpoint - 0.1)
                self.eci.update_setpoint(self.eci.setpoint - 0.1)

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
        port = '/dev/serial/by-id/usb-TTI_CPX400_Series_PSU_C2F952E5-if00'
        self.filament['device'] = CPX.CPX400DPDriver(1, device=port)
        self.filament['voltage'] = 0
        self.filament['current'] = 0
        self.filament['idle_voltage'] = 3
        self.filament['device'].set_current_limit(4)
        self.filament['device'].output_status(True)
        self.bias = {}
        self.bias['device'] = CPX.CPX400DPDriver(2, device=port)
        self.bias['grid_voltage'] = 0
        self.bias['grid_current'] = 0
        self.bias['device'].output_status(True)
        self.looptime = 0
        self.update_setpoint(0.1)
        i2c_helper = ABEHelpers()
        bus = i2c_helper.get_smbus()
        self.adc = DeltaSigma(bus, 0x68, 0x69, 18)
        self.adc.set_pga(1)  # This shold be 8, but amplifier seems broken on the available device
        self.running = True
        self.wanted_voltage = 0
        self.emission_current = 999
        self.pid = pid.PID(2, 0.03, 0, 9)
        self.pid.update_setpoint(self.setpoint)

    def set_bias(self, bias):
        """ Set the bias-voltage """
        if self.datasocket is not None:
            self.datasocket.set_point_now('ionenergy', bias)
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
        value = self.adc.read_voltage(5)
        self.measured_voltage = value
        current = 1000.0 * value / 3.4  # Resistance value read off component label
        return(current)

    def run(self):
        while self.running:
            #time.sleep(0.1)
            t = time.time()
            self.emission_current = self.read_emission_current()
            self.wanted_voltage = self.pid.wanted_power(self.emission_current) + self.filament['idle_voltage']
            self.pid.update_setpoint(self.setpoint)
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

    datasocket = DateDataPullSocket('emission_tof', ['setpoint', 'emission','ionenergy'], timeouts=[999999, 1.0,999999999])
    datasocket.start()

    ec = EmissionControl(datasocket)
    ec.set_bias(35)
    ec.start()

    tui = CursesTui(ec)
    tui.daemon = True
    tui.start()

