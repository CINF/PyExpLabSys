""" Temperature controller """
import time
import threading
import socket
import curses
import PyExpLabSys.auxiliary.pid as PID
import PyExpLabSys.drivers.cpx400dp as cpx
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.utilities import get_logger
import PyExpLabSys.common.utilities
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)
PyExpLabSys.common.utilities.ERROR_EMAIL = 'robert.jensen@fysik.dtu.dk'

LOGGER = get_logger('VHP Temperature control', level='INFO', file_log=True,
                    file_name='temp_control.log', terminal_log=False)

class CursesTui(threading.Thread):
    """ Text user interface for furnace heating control """
    def __init__(self, heating_class, heater):
        threading.Thread.__init__(self)
        self.start_time = time.time()
        self.quit = False
        self.hc = heating_class
        self.heager = heater
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)

    def run(self):
        while not self.quit:
            self.screen.addstr(3, 2, 'Running')
            val = self.hc.pc.setpoint
            self.screen.addstr(9, 40, "Setpoint: {0:.2f}C  ".format(val))
            val = self.hc.pc.temperature
            try:
                self.screen.addstr(9, 2, "Temeperature: {0:.1f}C  ".format(val))
            except (ValueError, TypeError):
                self.screen.addstr(9, 2, "Temeperature: -         ")
            val = self.hc.voltage * 2 # Two locked output channels
            self.screen.addstr(10, 2, "Wanted Voltage: {0:.2f}V  ".format(val))
            val = self.hc.actual_voltage * 2 # Two locked output channels
            self.screen.addstr(10, 40, "Actual Voltage: {0:.2f}V  ".format(val))
            val = self.hc.actual_current
            self.screen.addstr(11, 40, "Actual Current: {0:.2f}A  ".format(val))
            val = self.hc.actual_current * self.hc.actual_voltage * 2
            self.screen.addstr(12, 40, "Actual Power: {0:.2f}W  ".format(val))
            val = self.hc.pc.pid.setpoint
            self.screen.addstr(11, 2, "PID-setpint: {0:.2f}C  ".format(val))
            val = self.hc.pc.pid.integrated_error()
            self.screen.addstr(12, 2, "PID-error: {0:.3f}   ".format(val))
            val = self.hc.pc.pid.proportional_contribution()
            self.screen.addstr(13, 2, "P-term: {0:.3f}   ".format(val))
            val = self.hc.pc.pid.integration_contribution()
            self.screen.addstr(14, 2, "i-term: {0:.3f}   ".format(val))
            val = time.time() - self.start_time
            self.screen.addstr(18, 2, "Run time: {0:.0f}s".format(val))

            n = self.screen.getch()
            if n == ord('q'):
                self.hc.quit = True
                self.quit = True
            if n == ord('i'):
                self.hc.pc.update_setpoint(self.hc.pc.setpoint + 1)
            if n == ord('d'):
                self.hc.pc.update_setpoint(self.hc.pc.setpoint - 1)

            self.screen.refresh()
            time.sleep(0.2)
        self.stop()

    def stop(self):
        """ Clean up console """
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()


class PowerCalculatorClass(threading.Thread):
    """ Calculate the wanted amount of power """
    def __init__(self, pullsocket, pushsocket):
        threading.Thread.__init__(self)
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.power = 0
        self.setpoint = 50
        self.pid = PID.PID()
        self.pid.pid_p = 1
        self.pid.pid_i = 0.00075
        self.pid.p_max = 70
        self.update_setpoint(self.setpoint)
        self.quit = False
        self.temperature = None
        self.ramp = None

    def read_power(self):
        """ Return the calculated wanted power """
        return self.power

    def update_setpoint(self, setpoint=None):
        """ Update the setpoint """
        self.setpoint = setpoint
        self.pid.update_setpoint(setpoint)
        self.pullsocket.set_point_now('setpoint', setpoint)
        return setpoint
   
    def runner(self):
        """ Main thread loop """
        data_temp = 'vhp_T_reactor_outlet#raw'.encode('ascii')
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.2)

        while not self.quit:
            self.pullsocket.set_point_now('pid_p', self.pid.proportional_contribution())
            self.pullsocket.set_point_now('pid_i', self.pid.integration_contribution())
            self.pullsocket.set_point_now('pid_e', self.pid.integrated_error())

            error = 5
            while error > 0:
                try:
                    sock.sendto(data_temp, ('rasppi43', 9000))
                    received = sock.recv(1024).decode()
                    break # leave while loop, error will be > 0
                except socket.timeout:
                    LOGGER.error('Timeout Error: ' + str(error))
                    error = error - 1
                    time.sleep(0.25)

            LOGGER.info('Error value: {:f}'.format(error))
            if error > 0: # loop ended succesfully
                self.temperature = float(received[received.find(',') + 1:])
                self.power = self.pid.wanted_power(self.temperature)
            else:
                self.temperature = 9999
                self.power = 0

            #  Handle the setpoint from the network
            try:
                setpoint = self.pushsocket.last[1]['setpoint']
                new_update = self.pushsocket.last[0]
            except (TypeError, KeyError): #  Setpoint has never been sent
                setpoint = None
            if setpoint is not None:
                self.update_setpoint(setpoint)
            time.sleep(1)

    def run(self):
        try:
            self.runner()
        except:
            LOGGER.exception('VHP Power calculator failed')
            raise


class HeaterClass(threading.Thread):
    """ Do the actual heating """
    def __init__(self, power_calculator, pullsocket, power_supply):
        threading.Thread.__init__(self)
        self.pc = power_calculator
        self.heater = power_supply
        self.heater.output_status(True)
        self.pullsocket = pullsocket
        self.voltage = 0
        self.actual_voltage = 0
        self.actual_current = 0
        self.quit = False

    def runner(self):
        """ Main thread loop """
        time.sleep(0.05)
        while not self.quit:
            self.voltage = self.pc.read_power()
            self.pullsocket.set_point_now('voltage', 2*self.voltage)
            self.heater.set_voltage(self.voltage)
            self.actual_voltage = self.heater.read_actual_voltage()
            self.actual_current = self.heater.read_actual_current()
            time.sleep(0.5)
        self.heater.set_voltage(0)
        self.heater.output_status(False)

    def run(self):
        try:
            self.runner()
        except:
            LOGGER.exception('VHP Heater Class failed')
            raise

def main():
    """ Main function """
    power_supply = cpx.CPX400DPDriver(1, device='/dev/ttyACM0', interface='serial')
    power_supply.set_dual_output(False) # Synchronize outputs
    power_supply.set_current_limit(2.4)
    pullsocket = DateDataPullSocket('vhp_temp_control',
                                    ['setpoint', 'pid_p', 'pid_i', 'pid_e', 'voltage'],
                                    timeouts=[999999, 3.0, 3.0, 3.0, 3.0],
                                    port=9000)
    pullsocket.start()

    pushsocket = DataPushSocket('vhp_push_control', action='store_last')
    pushsocket.start()

    power_calc = PowerCalculatorClass(pullsocket, pushsocket)
    power_calc.daemon = True
    power_calc.start()

    heater = HeaterClass(power_calc, pullsocket, power_supply)
    heater.start()

    tui = CursesTui(heater, power_supply)
    tui.daemon = True
    tui.start()

if __name__ == '__main__':
    try:
        main()
    except:
        LOGGER.exception('Main program failed')
        raise
