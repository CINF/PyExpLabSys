""" Temperature controller """
import time
import threading
import socket
import curses
import pickle
import wiringpi as wp
import PyExpLabSys.auxiliary.pid as PID
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


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
            except (ValueError, TypeError):
                self.screen.addstr(9, 2, "Temeperature: -         ")
            val = self.hc.dutycycle
            self.screen.addstr(10, 2, "Wanted dutycycle: {0:.5f} ".format(val))
            val = self.hc.pc.pid.setpoint
            self.screen.addstr(11, 2, "PID-setpint: {0:.2f}C  ".format(val))
            val = self.hc.pc.pid.int_err
            self.screen.addstr(12, 2, "PID-error: {0:.3f} ".format(val))
            val = self.hc.pc.pid.pid_p * self.hc.pc.pid.error
            self.screen.addstr(11, 40, "PID-P: {0:.6f}    ".format(val))
            val = self.hc.pc.pid.pid_i * self.hc.pc.pid.int_err
            self.screen.addstr(12, 40, "PID-I: {0:.6f}    ".format(val))

            val = time.time() - self.start_time
            self.screen.addstr(15, 2, "Runetime: {0:.0f}s".format(val))

            key_val = self.screen.getch()
            if key_val == ord('q'):
                self.hc.quit = True
                self.quit = True
            if key_val == ord('i'):
                self.hc.pc.update_setpoint(self.hc.pc.setpoint + 1)
            if key_val == ord('d'):
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
        self.setpoint = 50
        self.pid = PID.PID(pid_p=0.013, pid_i=0.000015, p_max=1)
        self.update_setpoint(self.setpoint)
        self.quit = False
        self.temperature = None
        self.ramp = None

    def read_power(self):
        """ Return the calculated wanted power """
        return self.power

    def update_setpoint(self, setpoint=None, ramp=0):
        """ Update the setpoint """
        if ramp > 0:
            setpoint = self.ramp_calculator(time.time()-ramp)
        self.setpoint = setpoint
        self.pid.update_setpoint(setpoint)
        self.datasocket.set_point_now('setpoint', setpoint)
        return setpoint

    def ramp_calculator(self, current_time):
        """ Return the current valid setpoint calculated from the relevant ramp
        Also includes a default ramp for testing"""
        if self.ramp is None:
            self.ramp = {}
            self.ramp['temp'] = {}
            self.ramp['time'] = {}
            self.ramp['step'] = {}
            self.ramp['time'][0] = 20.0
            self.ramp['time'][1] = 2500.0
            self.ramp['time'][2] = 10800.0
            self.ramp['time'][3] = 10800.0
            self.ramp['time'][4] = 10800.0
            self.ramp['time'][5] = 10800.0
            self.ramp['temp'][0] = 0.0
            self.ramp['temp'][1] = 450.0
            self.ramp['temp'][2] = 0.0
            self.ramp['temp'][3] = 0.0
            self.ramp['temp'][4] = 0.0
            self.ramp['temp'][5] = 0.0
            self.ramp['step'][0] = True
            self.ramp['step'][1] = True
            self.ramp['step'][2] = True
            self.ramp['step'][3] = True
            self.ramp['step'][4] = False
            self.ramp['step'][4] = False
            self.ramp['step'][4] = False
        self.ramp['temp'][len(self.ramp['time'])] = 0
        self.ramp['step'][len(self.ramp['time'])] = True
        self.ramp['time'][len(self.ramp['time'])] = 999999999
        self.ramp['time'][-1] = 0
        self.ramp['temp'][-1] = 0
        i = 0
        while (current_time > 0) and (i < len(self.ramp['time'])):
            current_time = current_time - self.ramp['time'][i]
            i = i + 1
        i = i - 1
        current_time = current_time + self.ramp['time'][i]
        if self.ramp['step'][i] is True:
            return_value = self.ramp['temp'][i]
        else:
            time_frac = current_time / self.ramp['time'][i]
            return_value = self.ramp['temp'][i-1] + time_frac * (self.ramp['temp'][i] -
                                                                 self.ramp['temp'][i-1])
        return return_value

    def run(self):
        data_temp = b'fr307_furnace_1_T#raw'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        ramp_time = 0
        #ramp_time = time.time()
        sp_updatetime = 0
        ramp_updatetime = 0
        while not self.quit:
            sock.sendto(data_temp, ('localhost', 9001))
            received = sock.recv(1024).decode()
            self.temperature = float(received[received.find(',') + 1:])
            self.datasocket.set_point_now('temperature', self.temperature)
            self.power = self.pid.wanted_power(self.temperature)

            #  Handle the setpoint from the network
            try:
                setpoint = self.pushsocket.last[1]['setpoint']
                new_update = self.pushsocket.last[0]
            except (TypeError, KeyError): #  Setpoint has never been sent
                setpoint = None
            if ((setpoint is not None) and setpoint != self.setpoint) and \
               (sp_updatetime < new_update):
                self.update_setpoint(setpoint)
                sp_updatetime = new_update

            #  Handle the ramp from the network
            try:
                ramp = self.pushsocket.last[1]['ramp']
                new_update = self.pushsocket.last[0]
            except (TypeError, KeyError): #  Ramp has not yet been set
                ramp = None
            if ramp == 'stop':
                ramp_time = 0
            if (ramp is not None) and (ramp != 'stop'):
                try: # Python 3
                    # pylint: disable=unexpected-keyword-arg
                    ramp = pickle.loads(ramp.encode('ascii'),
                                        fix_imports=True)
                except TypeError: # Python 2
                    ramp = pickle.loads(ramp)
                if new_update > ramp_updatetime:
                    ramp_updatetime = new_update
                    self.ramp = ramp
                    ramp_time = time.time()
                else:
                    pass

            if ramp_time > 0:
                self.update_setpoint(ramp=ramp_time)
            time.sleep(0.5)


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
            self.datasocket.set_point_now('pid_p', self.pc.pid.proportional_contribution())
            self.datasocket.set_point_now('pid_i', self.pc.pid.integration_contribution())

            for i in range(0, self.beatsteps):
                time.sleep(1.0 * self.beatperiod / self.beatsteps)
                if i < self.beatsteps * self.dutycycle:
                    wp.digitalWrite(self.pinnumber, 1)
                else:
                    wp.digitalWrite(self.pinnumber, 0)
        wp.digitalWrite(self.pinnumber, 0)


def main():
    """ Main function """
    wp.wiringPiSetup()
    datasocket = DateDataPullSocket('furnaceroom_controller',
                                    ['temperature', 'setpoint', 'dutycycle', 'pid_p', 'pid_i'],
                                    timeouts=999999, port=9000)
    datasocket.start()

    pushsocket = DataPushSocket('furnaceroom_push_control', action='store_last')
    pushsocket.start()

    power_calculator = PowerCalculatorClass(datasocket, pushsocket)
    power_calculator.daemon = True
    power_calculator.start()

    heater = HeaterClass(power_calculator, datasocket)
    heater.start()

    tui = CursesTui(heater)
    tui.daemon = True
    tui.start()

if __name__ == '__main__':
    main()
