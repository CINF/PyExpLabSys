""" Temperature controller """
from __future__ import print_function
import time
import threading
import socket
import curses
import pickle
import PyExpLabSys.auxiliary.pid as PID
import PyExpLabSys.drivers.cpx400dp as cpx
import PyExpLabSys.drivers.agilent_34410A as dmm
import PyExpLabSys.auxiliary.rtd_calculator as rtd_calculator
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
                self.screen.addstr(9, 2, "Temeperature: {0:.4f}C  ".format(val))
            except ValueError:
                self.screen.addstr(9, 2, "Temeperature: -         ".format(val))
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

class RtdReader(threading.Thread):
    """ Read resistance of RTD and calculate temperature """
    def __init__(self, hostname, calib_temp):
        self.rtd_reader = dmm.Agilent34410ADriver(interface='lan',
                                                  hostname=hostname)
        self.rtd_reader.select_measurement_function('FRESISTANCE')
        self.calib_temp = calib_temp
        time.sleep(0.2)
        self.calib_value = self.rtd_reader.read()
        self.rtd_calc = rtd_calculator.RTD_Calculator(calib_temp,
                                                      self.calib_value)
        threading.Thread.__init__(self)
        self.temperature = None
        self.quit = False

    def value(self):
        """ Return current value of reader """
        return self.temperature

    def run(self):
        while not self.quit:
            time.sleep(0.1)
            rtd_value = self.rtd_reader.read()
            self.temperature = self.rtd_calc.find_temperature(rtd_value)


class PowerCalculatorClass(threading.Thread):
    """ Calculate the wanted amount of power """
    def __init__(self, pullsocket, pushsocket, value_reader):
        threading.Thread.__init__(self)
        self.value_reader = value_reader
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.power = 0
        self.setpoint = 9
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
        t = 0
        sp_updatetime = 0
        ramp_updatetime = 0
        while not self.quit:
            self.temperature = self.value_reader.value()
            self.pullsocket.set_point_now('temperature', self.temperature)
            self.power = self.pid.wanted_power(self.temperature)

            #  Handle the setpoint from the network
            try:
                setpoint = self.pushsocket.last[1]['setpoint']
                new_update = self.pushsocket.last[0]
                self.message = str(new_update)
            except (TypeError, KeyError): #  Setpoint has never been sent
                self.message = str(self.pushsocket.last)
                setpoint = None
            if (setpoint is not None) and (setpoint != self.setpoint) and (sp_updatetime < new_update):
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

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    try:
        temperature_string = 'mr_sample_tc_temperature#raw'
        sock.sendto(temperature_string.encode('ascii'), ('rasppi12', 9000))
        received = sock.recv(1024).decode('ascii')
        start_temp = float(received[received.find(',') + 1:])
        agilent_hostname = '10.54.6.79'
        rtd_reader = RtdReader(agilent_hostname, start_temp)
    except:
        print('Could not find rasppi12')
        exit()

    rtd_reader.daemon = True
    rtd_reader.start()
    time.sleep(1)

    PS = {}
    for k in range(1, 3):
        PS[k] = cpx.CPX400DPDriver(k, interface='serial', device='/dev/ttyACM0')
        PS[k].set_voltage(0)
        PS[k].output_status(True)

    try:
        micro = chr(0x03BC) # Python 3
    except ValueError:
        micro = unichr(0x03BC) # Python 2
    Pullsocket = DateDataPullSocket(micro + 'reactor temp_control',
                                    ['setpoint', 'voltage', 'temperature'], 
                                    timeouts=[999999, 3.0, 3.0],
                                    port=9000)
    Pullsocket.start()

    Pushsocket = DataPushSocket(micro + '-reactor push control', action='store_last')
    Pushsocket.start()

    pcc = PowerCalculatorClass(Pullsocket, Pushsocket, rtd_reader)
    pcc.daemon = True
    pcc.start()

    heater = HeaterClass(pcc, Pullsocket, PS)
    heater.start()

    tui = CursesTui(heater)
    tui.daemon = True
    tui.start()

if __name__ == '__main__':
    main()
