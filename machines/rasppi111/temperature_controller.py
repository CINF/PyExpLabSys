""" Temperature controller """
from __future__ import print_function
import time
import threading
import socket
import pickle
import PyExpLabSys.auxiliary.pid as PID
import PyExpLabSys.drivers.cpx400dp as cpx
import PyExpLabSys.drivers.agilent_34410A as dmm
import PyExpLabSys.auxiliary.rtd_calculator as rtd_calculator
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.utilities import activate_library_logging
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.microreactor_temperature_control import HeaterClass
from PyExpLabSys.common.microreactor_temperature_control import CursesTui
import PyExpLabSys.common.utilities
from PyExpLabSys.common.supported_versions import python2_and_3
PyExpLabSys.common.utilities.ERROR_EMAIL = 'robert.jensen@fysik.dtu.dk'
python2_and_3(__file__)

try:
    MICRO = chr(0x03BC) # Python 2
except ValueError:
    MICRO = unichr(0x03BC) # Python 2

LOGGER = get_logger(MICRO + '-reactor Temperature control', level='WARN', file_log=True,
                    file_name='temp_control.log', terminal_log=False, email_on_warnings=False)

activate_library_logging('PyExpLabSys.common.microreactor_temperature_control',
                         logger_to_inherit_from=LOGGER)
activate_library_logging('PyExpLabSys.auxiliary.pid', logger_to_inherit_from=LOGGER)

LOGGER.warn('Program started')

class RtdReader(threading.Thread):
    """ Read resistance of RTD and calculate temperature """
    def __init__(self, calib_temp):
        visa_string = 'usb0::2391::1543::MY47002726::INSTR'
        self.rtd_reader = dmm.Agilent34410ADriver(interface='usbtmc',
                                                  connection_string=visa_string)
        self.rtd_reader.select_measurement_function('FRESISTANCE')
        self.calib_temp = calib_temp
        time.sleep(0.2)
        self.calib_value = self.rtd_reader.read()
        self.rtd_calc = rtd_calculator.RtdCalculator(calib_temp,
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
        self.values = {}
        self.values['voltage'] = 0
        self.values['current'] = 0
        self.values['power'] = 0
        self.values['setpoint'] = -1
        self.values['temperature'] = None
        self.pid = PID.PID(pid_p=0.5, pid_i=0.2, p_max=54)
        self.update_setpoint(self.values['setpoint'])
        self.quit = False
        self.ramp = None

    def read_power(self):
        """ Return the calculated wanted power """
        return self.values['voltage']

    def update_setpoint(self, setpoint=None, ramp=0):
        """ Update the setpoint """
        if ramp > 0:
            setpoint = self.ramp_calculator(time.time()-ramp)
        self.values['setpoint'] = setpoint
        self.pid.update_setpoint(setpoint)
        self.pullsocket.set_point_now('setpoint', setpoint)
        return setpoint

    def ramp_calculator(self, ramp_time):
        """ Calculate the current ramp setpoint """
        ramp = self.ramp
        ramp['temp'][len(ramp['time'])] = 0
        ramp['step'][len(ramp['time'])] = True
        ramp['time'][len(ramp['time'])] = 999999999
        ramp['time'][-1] = 0
        ramp['temp'][-1] = 0
        i = 0
        #self.message = 'Klaf'
        while (ramp_time > 0) and (i < len(ramp['time'])):
            ramp_time = ramp_time - ramp['time'][i]
            i = i + 1
        i = i - 1
        ramp_time = ramp_time + ramp['time'][i]

        if ramp['step'][i] is True:
            return_value = ramp['temp'][i]
        else:
            time_frac = ramp_time / ramp['time'][i]
            return_value = ramp['temp'][i-1] + time_frac * (ramp['temp'][i] -
                                                            ramp['temp'][i-1])
        return return_value


    def run(self):
        current_time = 0
        sp_updatetime = 0
        ramp_updatetime = 0
        while not self.quit:
            self.values['temperature'] = self.value_reader.value()
            self.pullsocket.set_point_now('temperature', self.values['temperature'])
            self.values['voltage'] = self.pid.wanted_power(self.values['temperature'])

            #  Handle the setpoint from the network
            try:
                setpoint = self.pushsocket.last[1]['setpoint']
                new_update = self.pushsocket.last[0]
            except (TypeError, KeyError): #  Setpoint has never been sent
                setpoint = None
            if ((setpoint is not None) and
                (setpoint != self.values['setpoint']) and (sp_updatetime < new_update)):
                self.update_setpoint(setpoint)
                sp_updatetime = new_update

            #  Handle the ramp from the network
            try:
                ramp = self.pushsocket.last[1]['ramp']
                new_update = self.pushsocket.last[0]

            except (TypeError, KeyError): #  Ramp has not yet been set
                ramp = None
            if ramp == 'stop':
                current_time = 0
            if (ramp is not None) and (ramp != 'stop'):
                ramp = pickle.loads(ramp)
                if new_update > ramp_updatetime:
                    ramp_updatetime = new_update
                    self.ramp = ramp
                    current_time = time.time()
                else:
                    pass
            if current_time > 0:
                self.update_setpoint(ramp=current_time)
            time.sleep(1)


def main():
    """ Main function """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    try:
        temperature_string = 'mr_sample_tc_temperature#raw'
        sock.sendto(temperature_string.encode('ascii'), ('rasppi12', 9000))
        received = sock.recv(1024).decode('ascii')
        start_temp = float(received[received.find(',') + 1:])
    except socket.gaierror:
        print('Could not find rasppi12')
        exit()
    except ValueError:
        print('Bad reply from rasppi12')
        exit()
    rtd_reader = RtdReader(start_temp)

    rtd_reader.daemon = True
    rtd_reader.start()
    time.sleep(1)

    power_supply = {}
    for k in range(1, 3):
        power_supply[k] = cpx.CPX400DPDriver(k, interface='serial', device='/dev/ttyACM0')
        power_supply[k].set_voltage(0)
        power_supply[k].output_status(True)

    codenames = ['setpoint', 'wanted_voltage', 'actual_voltage_1', 'actual_voltage_2',
                 'actual_current_1', 'actual_current_2', 'power', 'temperature']
    pullsocket = DateDataPullSocket(MICRO + '-reactor_temp_control', codenames,
                                    timeouts=[999999, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0])
    pullsocket.start()

    pushsocket = DataPushSocket(MICRO + '-reactor push control', action='store_last')
    pushsocket.start()

    power_calculator = PowerCalculatorClass(pullsocket, pushsocket, rtd_reader)
    power_calculator.daemon = True
    power_calculator.start()

    heater = HeaterClass(power_calculator, pullsocket, power_supply)
    heater.start()

    tui = CursesTui(heater)
    tui.daemon = True
    tui.start()

if __name__ == '__main__':
    main()
