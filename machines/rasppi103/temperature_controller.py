# pylint: disable=R0913,W0142,C0103

""" Temperature controller """
import time
import threading
import socket
import curses
import pickle
import PyExpLabSys.auxiliary.pid as PID
import PyExpLabSys.drivers.cpx400dp as cpx
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket


class CursesTui(threading.Thread):
    """ Text user interface for furnace heating control """
    def __init__(self, heating_class):
        threading.Thread.__init__(self)
        self.start_time = time.time()
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
            val = self.hc.pc.setpoint
            self.screen.addstr(9, 40, "Setpoint: {0:.2f}C  ".format(val))
            val = self.hc.pc.temperature
            try:
                self.screen.addstr(9, 2, "Temperature: {0:.4f}C  ".format(val))
            except (ValueError, TypeError):
                self.screen.addstr(9, 2, "Temperature: -         ")
            val = self.hc.voltage
            self.screen.addstr(10, 2, "Actual Voltage: {0:.2f} ".format(val))
            val = self.hc.pc.pid.setpoint
            self.screen.addstr(11, 2, "PID-setpint: {0:.2f}C  ".format(val))
            val = self.hc.pc.pid.int_err
            self.screen.addstr(12, 2, "PID-error: {0:.3f} ".format(val))
            val = time.time() - self.start_time
            self.screen.addstr(15, 2, "Runetime: {0:.0f}s".format(val))

            self.screen.addstr(17, 2, "Message:" + self.hc.pc.message)

            self.screen.addstr(20, 2, "Message:" + self.hc.pc.message2)

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
        self.setpoint = 0
        self.pid = PID.PID()
        self.pid.Kp = 0.20
        self.pid.Ki = 0.05
        self.pid.Pmax = 45
        self.update_setpoint(self.setpoint)
        self.quit = False
        self.temperature = None
        self.ramp = None
        self.message = '**'
        self.message2 = '*'

    def read_power(self):
        """ Return the calculated wanted power """
        return self.power

    def update_setpoint(self, setpoint=None, ramp=0):
        """ Update the setpoint """
        if ramp > 0:
            setpoint = self.ramp_calculator(time.time()-ramp)
        self.setpoint = setpoint
        self.pid.update_setpoint(setpoint)
        self.pullsocket.set_point_now('setpoint', setpoint)
        return setpoint

    def ramp_calculator(self, time):
        ramp = self.ramp
        ramp['temp'][len(ramp['time'])] = 0
        ramp['step'][len(ramp['time'])] = True
        ramp['time'][len(ramp['time'])] = 999999999
        ramp['time'][-1] = 0
        ramp['temp'][-1] = 0
        i = 0
        #self.message = 'Klaf'
        while (time > 0) and (i < len(ramp['time'])):
            time = time - ramp['time'][i]
            i = i + 1
        i = i - 1
        time = time + ramp['time'][i]
        #self.message2 = 'Klaf'
        if ramp['step'][i] is True:
            return_value = ramp['temp'][i]
        else:
            time_frac = time / ramp['time'][i]
            return_value = ramp['temp'][i-1] + time_frac * (ramp['temp'][i] -
                                                            ramp['temp'][i-1])
        return return_value


    def run(self):
        data_temp = 'mgw_reactor_tc_temperature#raw'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        t = 0
        sp_updatetime = 0
        ramp_updatetime = 0
        while not self.quit:
            sock.sendto(data_temp.encode('ascii'), ('localhost', 9001))
            received = sock.recv(1024).decode()
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
            if ((setpoint is not None) and
                (setpoint != self.setpoint) and (sp_updatetime < new_update)):
                self.update_setpoint(setpoint)
                sp_updatetime = new_update

            #  Handle the ramp from the network
            try:
                ramp = self.pushsocket.last[1]['ramp']
                new_update = self.pushsocket.last[0]
                self.message2 = str(new_update)

            except (TypeError, KeyError): #  Ramp has not yet been set
                ramp = None
            if ramp == 'stop':
                t = 0
            if (ramp is not None) and (ramp != 'stop'):
                ramp = pickle.loads(ramp)
                if new_update > ramp_updatetime:
                    ramp_updatetime = new_update
                    self.ramp = ramp
                    t = time.time()
                else:
                    pass
            if t > 0:
                self.update_setpoint(ramp=t)
            time.sleep(1)


class HeaterClass(threading.Thread):
    """ Do the actual heating """
    def __init__(self, power_calculator, pullsocket, ps):
        threading.Thread.__init__(self)
        self.pc = power_calculator
        self.pullsocket = pullsocket
        self.ps = ps
        self.voltage = 0
        self.quit = False

    def run(self):
        while not self.quit:
            self.voltage = self.pc.read_power()
            self.pullsocket.set_point_now('voltage', self.voltage)
            for i in range(1, 3):
                self.ps[i].set_voltage(self.voltage)
            time.sleep(0.25)
        for i in range(1, 3):
            self.ps[i].set_voltage(0)
            self.ps[i].output_status(False)

port = '/dev/serial/by-id/usb-TTI_CPX400_Series_PSU_55126216-if00'
PS = {}
for i in range(1, 3):
    PS[i] = cpx.CPX400DPDriver(i, interface='lan',
                               hostname='cinf-palle-heating-ps',
                               tcp_port=9221)
    PS[i].set_voltage(0)
    PS[i].output_status(True)

Pullsocket = DateDataPullSocket('mgw_temp_control',
                                ['setpoint', 'voltage'],
                                timeouts=[999999, 3.0],
                                port=9000)
Pullsocket.start()

Pushsocket = DataPushSocket('mgw_push_control', action='store_last')
Pushsocket.start()

P = PowerCalculatorClass(Pullsocket, Pushsocket)
P.daemon = True
P.start()

H = HeaterClass(P, Pullsocket, PS)
#H.daemon = True
H.start()

T = CursesTui(H)
T.daemon = True
T.start()
