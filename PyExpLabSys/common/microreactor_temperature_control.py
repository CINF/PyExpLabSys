""" Common code for microreactor heaters """
import time
import threading
import logging
import curses
from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

class CursesTui(threading.Thread):
    """ Text user interface for heater heating control """
    def __init__(self, heating_class):
        threading.Thread.__init__(self)
        self.start_time = time.time()
        self.quit = False
        self.heater = heating_class
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)

    def run(self):
        while not self.quit:
            self.screen.addstr(3, 2, 'Running')
            val = self.heater.power_calculator.values['setpoint']
            self.screen.addstr(9, 40, "Setpoint: {0:.2f}C  ".format(val))
            val = self.heater.power_calculator.values['temperature']
            try:
                self.screen.addstr(9, 2, "Temeperature: {0:.4f}C  ".format(val))
            except (ValueError, TypeError):
                self.screen.addstr(9, 2, "Temeperature: -         ")
            val = self.heater.values['wanted_voltage']
            self.screen.addstr(10, 2, "Wanted Voltage: {0:.2f} ".format(val))
            val = self.heater.power_calculator.pid.setpoint
            self.screen.addstr(11, 2, "PID-setpint: {0:.2f}C  ".format(val))
            val = self.heater.power_calculator.pid.int_err
            self.screen.addstr(12, 2, "PID-error: {0:.3f} ".format(val))
            val = time.time() - self.start_time
            self.screen.addstr(15, 2, "Runetime: {0:.0f}s".format(val))

            val = self.heater.values['actual_voltage_1']
            self.screen.addstr(11, 40, "Actual Voltage 1: {0:.2f}V           ".format(val))
            val = self.heater.values['actual_voltage_2']
            self.screen.addstr(12, 40, "Actual Voltage 2: {0:.2f}V          ".format(val))
            val = self.heater.values['actual_current_1'] * 1000
            self.screen.addstr(13, 40, "Actual Current 1: {0:.0f}mA          ".format(val))
            val = self.heater.values['actual_current_2'] * 1000
            self.screen.addstr(14, 40, "Actual Current 2: {0:.0f}mA         ".format(val))
            power1 = (self.heater.values['actual_voltage_1'] *
                      self.heater.values['actual_current_1'])
            self.screen.addstr(15, 40, "Power, heater 1: {0:.3f}W           ".format(power1))
            power2 = (self.heater.values['actual_voltage_2'] *
                      self.heater.values['actual_current_2'])
            
            self.screen.addstr(16, 40, "Power, heater 2: {0:.3f}W           ".format(power2))
            self.screen.addstr(17, 40, "Total Power1: {0:.3f}W        ".format(
                power1 + power2))

            self.screen.addstr(19, 2, "Keys: (i)ncrement, (d)ecrement and (q)uit")

            
            key_val = self.screen.getch()
            if key_val == ord('q'):
                self.heater.quit = True
                self.quit = True
            if key_val == ord('i'):
                self.heater.power_calculator.update_setpoint(
                    self.heater.power_calculator.values['setpoint'] + 1)
            if key_val == ord('d'):
                self.heater.power_calculator.update_setpoint(
                    self.heater.power_calculator.values['setpoint'] - 1)

            self.screen.refresh()
            time.sleep(0.2)
        self.stop()
        LOGGER.info('TUI ended')

    def stop(self):
        """ Clean up console """
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()
        time.sleep(0.5)


class HeaterClass(threading.Thread):
    """ Do the actual heating """
    def __init__(self, power_calculator, pullsocket, power_supply):
        threading.Thread.__init__(self)
        self.power_calculator = power_calculator
        self.pullsocket = pullsocket
        self.power_supply = power_supply
        self.values = {}
        self.values['wanted_voltage'] = 0
        self.values['actual_voltage_1'] = 0
        self.values['actual_voltage_2'] = 0
        self.values['actual_current_1'] = 0
        self.values['actual_current_2'] = 0
        self.quit = False

    def run(self):
        while not self.quit:
            self.values['wanted_voltage'] = self.power_calculator.read_power()
            self.pullsocket.set_point_now('wanted_voltage', self.values['wanted_voltage'])
            self.power_supply[1].set_voltage(self.values['wanted_voltage'])
            time.sleep(0.1)
            self.power_supply[2].set_voltage(self.values['wanted_voltage'] * 0.5)

            ps_value = -11
            while ps_value < -10:
                ps_value = self.power_supply[1].read_actual_voltage()
                LOGGER.info('Voltage 1: ' + str(ps_value))
            self.values['actual_voltage_1'] = ps_value
            self.pullsocket.set_point_now('actual_voltage_1', ps_value)
            time.sleep(0.5)
            ps_value = -11
            while ps_value < -10:
                ps_value = self.power_supply[1].read_actual_current()
            self.values['actual_current_1'] = ps_value
            self.pullsocket.set_point_now('actual_current_1', ps_value)
            time.sleep(0.5)
            ps_value = -11
            while ps_value < -10:
                ps_value = self.power_supply[2].read_actual_voltage()
                LOGGER.info(ps_value)
            self.values['actual_voltage_2'] = ps_value
            self.pullsocket.set_point_now('actual_voltage_2', ps_value)
            time.sleep(0.5)
            ps_value = -11
            while ps_value < -10:
                ps_value = self.power_supply[2].read_actual_current()
            self.values['actual_current_2'] = ps_value
            self.pullsocket.set_point_now('actual_current_2', ps_value)
            time.sleep(0.5)
        for i in range(1, 3):
            self.power_supply[i].set_voltage(0)
            LOGGER.info('%s set voltage', i)
            self.power_supply[i].output_status(False)
            LOGGER.info('%s output status', i)
        self.stop()

    def stop(self):
        """ Clean up """
        time.sleep(0.5)
