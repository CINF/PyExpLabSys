
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
            self.screen.addstr(9, 40, "Setpoint: {0:.2f}C  ".format(val))
            val = self.hc.pc.temperature
            try:
                self.screen.addstr(9, 2, "Temeperature: {0:.1f}C  ".format(val))
            except ValueError:
                self.screen.addstr(9, 2, "Temeperature: -         ".format(val))
            val = self.hc.dutycycle
            self.screen.addstr(10, 2, "Wanted dutycycle: {0:.5f} ".format(val))
            val = self.hc.pc.pid.setpoint
            self.screen.addstr(11, 2, "PID-setpint: {0:.2f}C  ".format(val))
            val = self.hc.pc.pid.IntErr
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
        self.message = '*'
        self.message2 = '*'

    def read_power(self):
        """ Return the calculated wanted power """
        return(self.power)

    def update_setpoint(self, setpoint=None, ramp=0):
        """ Update the setpoint """
        if ramp > 0:
            setpoint = self.ramp_calculator(time.time()-ramp)
        self.setpoint = setpoint
        self.pid.UpdateSetpoint(setpoint)
        self.datasocket.set_point_now('setpoint', setpoint)
        return setpoint

    """
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
        return return_value
    """

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
            return_value = ramp['temp'][i-1] + time_frac * (ramp['temp'][i] - ramp['temp'][i-1])
        return return_value


    def run(self):
        data_temp = 'T1#raw'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        t = 0
        sp_updatetime = 0
        ramp_updatetime = 0
        while not self.quit:
            sock.sendto(data_temp, ('localhost', 9001))
            received = sock.recv(1024)
            self.temperature = float(received[received.find(',') + 1:])
            self.power = self.pid.WantedPower(self.temperature)

            #  Handle the setpoint from the network
            try:
                setpoint = self.pushsocket.last[1]['setpoint']
                new_update = self.pushsocket.last[0]
                self.message = str(new_update)
            except (TypeError, KeyError): #  Setpoint has never been sent
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
T.daemon = True
T.start()

