# pylint: disable=R0913,W0142,C0103

""" Temperature controller """
import time
import threading
import socket
import curses
import PyExpLabSys.auxiliary.pid as PID
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket

class PulseHeater(threading.Thread):
    """ PWM class for simple heater """
    def __init__(self):
        threading.Thread.__init__(self)
        self.dc = 0
        self.quit = False

    def set_dc(self, dc):
        """ Set the duty cycle """
        self.dc = dc

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        steps = 500
        state = False
        data = 'raw_wn#9:bool:'
        while not self.quit:
            for i in range(0, steps):
                if (1.0*i/steps < self.dc) and (state is False):
                    sock.sendto(data + 'True', ('rasppi33', 8500))
                    #received = sock.recv(1024)
                    state = True
                if (1.0*i/steps > self.dc) and (state is True):
                    sock.sendto(data + 'False', ('rasppi33', 8500))
                    #received = sock.recv(1024)
                    state = False
                time.sleep(5.0 / steps)
        sock.sendto(data + 'False', ('rasppi33', 9999))

class CursesTui(threading.Thread):
    """ Text user interface for furnace heating control """
    def __init__(self, heating_class, ph):
        threading.Thread.__init__(self)
        self.start_time = time.time()
        self.quit = False
        self.hc = heating_class
        self.ph = ph
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
            except ValueError:
                self.screen.addstr(9, 2, "Temeperature: -         ".format(val))
            val = self.hc.dutycycle
            self.screen.addstr(10, 2, "Actual Dutycycle: {0:.2f} ".format(val))
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
            self.screen.addstr(19, 2, "Message:" + self.hc.pc.message)
            self.screen.addstr(20, 2, "Message:" + self.hc.pc.message2)

            n = self.screen.getch()
            if n == ord('q'):
                self.hc.quit = True
                self.ph.quit = True
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
        self.pid.pid_p = 0.003
        self.pid.pid_i = 0.0000037
        self.pid.p_max = 0.5
        self.update_setpoint(self.setpoint)
        self.quit = False
        self.temperature = None
        self.ramp = None
        self.message = '**'
        self.message2 = '*'

    def read_power(self):
        """ Return the calculated wanted power """
        return(self.power)

    def update_setpoint(self, setpoint=None):
        """ Update the setpoint """
        self.setpoint = setpoint
        self.pid.update_setpoint(setpoint)
        self.pullsocket.set_point_now('setpoint', setpoint)
        return setpoint

    def run(self):
        data_temp = 'vhp_T_reactor_outlet#raw'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        while not self.quit:
            self.pullsocket.set_point_now('pid_p', self.pid.proportional_contribution())
            self.pullsocket.set_point_now('pid_i', self.pid.integration_contribution())
            self.pullsocket.set_point_now('pid_e', self.pid.integrated_error())

            sock.sendto(data_temp, ('localhost', 9000))
            received = sock.recv(1024)
            self.temperature = float(received[received.find(',') + 1:])
            self.power = self.pid.wanted_power(self.temperature)

            #  Handle the setpoint from the network
            try:
                setpoint = self.pushsocket.last[1]['setpoint']
                new_update = self.pushsocket.last[0]
                self.message = str(new_update)
            except (TypeError, KeyError): #  Setpoint has never been sent
                self.message = str(self.pushsocket.last)
                setpoint = None
            if setpoint is not None:
                self.update_setpoint(setpoint)
            time.sleep(1)


class HeaterClass(threading.Thread):
    """ Do the actual heating """
    def __init__(self, power_calculator, pullsocket, heater):
        threading.Thread.__init__(self)
        self.pc = power_calculator
        self.heater = heater
        self.pullsocket = pullsocket
        self.dutycycle = 0
        self.quit = False

    def run(self):
        while not self.quit:
            self.dutycycle = self.pc.read_power()
            self.pullsocket.set_point_now('dutycycle', self.dutycycle)
            self.heater.set_dc(self.dutycycle)
            time.sleep(0.5)
        self.heater.set_dc(0)

PH = PulseHeater()
PH.start()

Pullsocket = DateDataPullSocket('vhp_temp_control',
                                ['setpoint', 'dutycycle','pid_p', 'pid_i', 'pid_e'], 
                                timeouts=[999999, 3.0, 3.0, 3.0, 3.0],
                                port=9001)
Pullsocket.start()

Pushsocket = DataPushSocket('vhp_push_control', action='store_last')
Pushsocket.start()

P = PowerCalculatorClass(Pullsocket, Pushsocket)
P.daemon = True
P.start()

H = HeaterClass(P, Pullsocket, PH)
H.start()


T = CursesTui(H, PH)
T.daemon = True
T.start()

