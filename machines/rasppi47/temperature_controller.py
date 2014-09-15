# pylint: disable=R0913,W0142,C0103

""" Temperature controller """
import time
import threading
import socket
import curses
import pickle
import wiringpi2 as wp
import PyExpLabSys.auxiliary.pid as PID
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
            self.screen.addstr(9, 40, "Setpoint: {0:.2f}C".format(val))
            val = self.hc.pc.temperature
            self.screen.addstr(9, 2, "Temeperature: {0:.1f}C".format(val))
            val = self.hc.dutycycle
            self.screen.addstr(10, 2, "Wanted dutycycle: {0:.5f}".format(val))
            val = self.hc.pc.pid.setpoint
            self.screen.addstr(11, 2, "PID-setpint: {0:.2f}C".format(val))
            val = self.hc.pc.pid.IntErr
            self.screen.addstr(12, 2, "PID-error: {0:.3f}".format(val))
            val = time.time() - self.start_time
            self.screen.addstr(15, 2, "Runetime: {0:.0f}s".format(val))

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
    def __init__(self, datasocket, pushsocket):
        threading.Thread.__init__(self)
        self.datasocket = datasocket
        self.pushsocket = pushsocket
        self.power = 0
        self.setpoint = 150
        self.pid = PID.PID()
        self.pid.Kp = 0.0150
        self.pid.Ki = 0.0001
        self.pid.Pmax = 1
        self.update_setpoint(self.setpoint)
        self.quit = False
        self.temperature = None
        self.ramp = None

    def read_power(self):
        """ Return the calculated wanted power """
        return(self.power)

    def update_setpoint(self, setpoint=None, ramp=0):
        """ Update the setpoint """
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        if (setpoint is None) and (ramp == 0):
            data = 'read_setpoint'
            sock.sendto(data, ('130.225.87.157', 9999))
            received = sock.recv(1024)
            setpoint = float(received)
        if ramp > 0:
            setpoint = self.ramp_calculator(time.time()-ramp)
        data = 'set_setpoint' + str(setpoint)
        sock.sendto(data, ('130.225.87.157', 9999))
        """
        self.setpoint = setpoint
        self.pid.UpdateSetpoint(setpoint)
        self.datasocket.set_point_now('setpoint', setpoint)
        return setpoint


    def ramp_calculator(self, time):
        if self.ramp is None:
            self.ramp['temp'] = {}
            self.ramp['time'] = {}
            self.ramp['step'] = {}
            self.ramp['time'][0] = 20.0
            self.ramp['time'][1] = 35.0
            self.ramp['time'][2] = 30.0
            self.ramp['time'][3] = 25.0
            self.ramp['time'][4] = 35.0
            self.ramp['temp'][0] = 100.0
            self.ramp['temp'][1] = 50.0
            self.ramp['temp'][2] = 60.0
            self.ramp['temp'][3] = 90.0
            self.ramp['temp'][4] = 70.0
            self.ramp['step'][0] = False
            self.ramp['step'][1] = False
            self.ramp['step'][2] = True
            self.ramp['step'][3] = False
            self.ramp['step'][4] = True
        self.ramp['temp'][len(self.ramp['time'])] = 0
        self.ramp['step'][len(self.ramp['time'])] = True
        self.ramp['time'][len(self.ramp['time'])] = 999999999
        self.ramp['time'][-1] = 0
        self.ramp['temp'][-1] = 0
        i = 0
        while (time > 0) and (i < len(self.ramp['time'])):
            time = time - self.ramp['time'][i]
            i = i + 1
        i = i - 1
        time = time + self.ramp['time'][i]
        if self.ramp['step'][i] is True:
            return_value = self.ramp['temp'][i]
        else:
            time_frac = time / self.ramp['time'][i]
            return_value = self.ramp['temp'][i-1] + time_frac * (self.ramp['temp'][i] - self.ramp['temp'][i-1])
        return(return_value)

    def run(self):
        data_temp = 'T1#raw'
        data_ramp = 'read_ramp'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        t = 0
        pushupdatetime = 0
        while not self.quit:
            sock.sendto(data_temp, ('localhost', 9001))
            received = sock.recv(1024)
            self.temperature = float(received[received.find(',') + 1:])
            self.power = self.pid.WantedPower(self.temperature)
            try:
                setpoint = self.pushsocket.last[1]['setpoint']
                new_update = self.pushsocket.last[0]
            except TypeError:
                setpoint = None
            if (setpoint is not None) and (setpoint != self.setpoint) and (pushupdatetime < new_update):
                self.update_setpoint(setpoint)
                pushupdatetime = new_update
            

            """
            sock.sendto(data_ramp, ('localhost', 9999))
            received = sock.recv(1024)
            if not ((received == '') or (received == 'stop')):
                self.ramp = pickle.loads(received)
                t = time.time()
            if received == 'stop':
                t = 0
            if t > 0:
                self.update_setpoint(ramp=t)
            else:
                self.update_setpoint()
            """
            time.sleep(1)


class HeaterClass(threading.Thread):
    """ Do the actual heating """
    def __init__(self, power_calculator, datasocket):
        threading.Thread.__init__(self)
        self.pinnumber = 0
        self.pc = power_calculator
        self.datasocket = datasocket
        self.beatperiod = 5 # seconds
        self.beatsteps = 100
        self.dutycycle = 0
        self.quit = False
        wp.pinMode(self.pinnumber, 1)  # Set pin 0 to output

    def run(self):
        while not self.quit:
            self.dutycycle = self.pc.read_power()
            self.datasocket.set_point_now('dutycycle', self.dutycycle)
            for i in range(0, self.beatsteps):
                time.sleep(1.0 * self.beatperiod / self.beatsteps)
                if i < self.beatsteps * self.dutycycle:
                    wp.digitalWrite(self.pinnumber, 1)
                else:
                    wp.digitalWrite(self.pinnumber, 0)
        wp.digitalWrite(self.pinnumber, 0)


wp.wiringPiSetup()
datasocket = DateDataPullSocket('furnaceroom_controller',
                                ['setpoint', 'dutycycle'], 
                                timeouts=[999999, 3.0],
                                port=9000)
datasocket.start()

pushsocket = DataPushSocket('furnaceroom_push_control', action='store_last')
pushsocket.start()

P = PowerCalculatorClass(datasocket, pushsocket)
#print P.ramp_calculator(2)
#print P.ramp_calculator(2000)
P.daemon = True
P.start()

H = HeaterClass(P, datasocket)
#H.daemon = True
H.start()

T = CursesTui(H)
#T.daemon = True
T.start()

