""" Text gui for emission control """
import time
import threading
import curses

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
            string = "Grid Voltage: {0:.4f}V       "
            self.screen.addstr(8, 2, string.format(self.eci.bias['grid_voltage']))
            string = "Grid Current: {0:.3f}A       "
            self.screen.addstr(8, 40, string.format(self.eci.bias['grid_current']))
            string = "Emission current: {0:.6f}mA    "
            self.screen.addstr(12, 2, string.format(self.eci.emission_current))
            string = "Setpoint: {0:.2f}mA"
            self.screen.addstr(12, 40, string.format(self.eci.setpoint))
            try:
                string = "Update rate: {0:.1f}Hz    "
                self.screen.addstr(14, 2, string.format(1 / self.eci.looptime))
            except ZeroDivisionError:
                pass

            key_val = self.screen.getch()
            if key_val == ord('q'):
                self.eci.running = False
            if key_val == ord('i'):
                self.eci.update_setpoint(self.eci.setpoint + 0.1)
            if key_val == ord('d'):
                #self.eci.setpoint = self.eci.update_setpoint(self.eci.setpoint - 0.1)
                self.eci.update_setpoint(self.eci.setpoint - 0.1)
            if key_val == ord('I'):
                self.eci.update_setpoint(self.eci.setpoint + 0.01)
            if key_val == ord('D'):
                self.eci.update_setpoint(self.eci.setpoint - 0.01)

            self.screen.refresh()
            time.sleep(0.2)

    def stop(self):
        """ Reset the terminal """
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()

