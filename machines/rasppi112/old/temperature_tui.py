# pylint: disable=R0913,W0142,C0103

""" Temperature controller """
import time
import threading
import curses



class CursesTui(threading.Thread):
    """ Text user interface for furnace heating control """
    def __init__(self, heating_classes):
        threading.Thread.__init__(self)
        self.start_time = time.time()
        self.quit = False
        self.hc = heating_classes
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)

    def run(self):
        while not self.quit:
            for i in range(0, len(self.hc)):
                self.screen.addstr(3+10*i, 2, 'Running - ' + self.hc[i].ps_name)
                val = self.hc[i].pc.setpoint
                self.screen.addstr(4+10*i, 30, "Setpoint: {0:.2f}C  ".format(val))
                val = self.hc[i].pc.temperature
                try:
                    self.screen.addstr(4+10*i, 2, "Temeperature: {0:.1f}C  ".format(val))
                except ValueError:
                    self.screen.addstr(4+10*i, 2, "Temeperature: -         ".format(val))
                val = self.hc[i].actual_voltage
                self.screen.addstr(5+10*i, 2, "Actual Voltage: {0:.2f} ".format(val))
                val = self.hc[i].current
                self.screen.addstr(5+10*i, 30, "Actual Current: {0:.2f} ".format(val))
                val = self.hc[i].pc.pid.setpoint
                self.screen.addstr(6+10*i, 2, "PID-setpint: {0:.2f}C  ".format(val))
                val = self.hc[i].pc.pid.int_err
                self.screen.addstr(7+10*i, 2, "PID-error: {0:.3f} ".format(val))

            val = time.time() - self.start_time
            self.screen.addstr(30, 2, "Runtime: {0:.0f}s".format(val))

            n = self.screen.getch()
            if n == ord('q'):
                for i in range(0, len(self.hc)):
                    self.hc[i].quit = True
                self.quit = True
            if n == ord('i'):
                self.hc[0].pc.update_setpoint(self.hc[0].pc.setpoint + 1)
            if n == ord('d'):
                self.hc[0].pc.update_setpoint(self.hc[0].pc.setpoint - 1)

            self.screen.refresh()
            time.sleep(0.2)
        self.stop()

    def stop(self):
        """ Clean up console """
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()
