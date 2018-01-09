""" Temperature controller"""
import time
import threading
import socket
import pickle
import PyExpLabSys.auxiliary.pid as PID
import PyExpLabSys.drivers.cpx400dp as cpx
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.microreactor_temperature_control import HeaterClass
from PyExpLabSys.common.microreactor_temperature_control import CursesTui
from PyExpLabSys.common.utilities import activate_library_logging
import PyExpLabSys.common.utilities
from PyExpLabSys.common.supported_versions import python2_and_3
PyExpLabSys.common.utilities.ERROR_EMAIL = 'robert.jensen@fysik.dtu.dk'
python2_and_3(__file__)

LOGGER = get_logger('Palle Temperature control', level='WARN', file_log=True,
                    file_name='temp_control.log', terminal_log=False, email_on_warnings=False)


activate_library_logging('PyExpLabSys.common.microreactor_temperature_control',
                         logger_to_inherit_from=LOGGER)
activate_library_logging('PyExpLabSys.auxiliary.pid', logger_to_inherit_from=LOGGER)

LOGGER.warn('Program started')

class PowerCalculatorClass(threading.Thread):
    """ Calculate the wanted amount of power """
    def __init__(self, pullsocket, pushsocket):
        threading.Thread.__init__(self)
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.pushsocket = pushsocket
        self.values = {}
        self.values['power'] = 0
        self.values['setpoint'] = -1
        self.values['temperature'] = None
        self.pid = PID.PID(pid_p=0.2, pid_i=0.05, pid_d=0, p_max=45)
        self.update_setpoint(self.values['setpoint'])
        self.quit = False
        self.ramp = None
        self.message = '**'
        self.message2 = '*'

    def read_power(self):
        """ Return the calculated wanted power """
        return self.values['power']

    def update_setpoint(self, setpoint=None, ramp=0):
        """ Update the setpoint """
        if ramp > 0:
            setpoint = self.ramp_calculator(time.time()-ramp)
        self.values['setpoint'] = setpoint
        LOGGER.debug('Setting setpoint:' + str(setpoint))
        self.pid.update_setpoint(setpoint)
        LOGGER.debug('Setpoint correct')
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
        LOGGER.debug('Start Power Calculator')
        LOGGER.debug(self.quit)
        data_temp = 'mgw_reactor_tc_temperature#raw'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        t = 0
        sp_updatetime = 0
        ramp_updatetime = 0
        while not self.quit:
            sock.sendto(data_temp.encode('ascii'), ('localhost', 9001))
            received = sock.recv(1024).decode()
            LOGGER.debug(received)
            self.values['temperature'] = float(received[received.find(',') + 1:])
            LOGGER.debug('Temperature: ' + str(self.values['temperature']))
            self.values['power'] = self.pid.wanted_power(self.values['temperature'])
            LOGGER.debug('b')
            LOGGER.debug('Power: ' + str(self.values['power']))
            #  Handle the setpoint from the network
            try:
                setpoint = self.pushsocket.last[1]['setpoint']
                new_update = self.pushsocket.last[0]
                self.message = str(new_update)
            except (TypeError, KeyError): #  Setpoint has never been sent
                self.message = str(self.pushsocket.last)
                setpoint = None
            if ((setpoint is not None) and
            (setpoint != self.values['setpoint']) and (sp_updatetime < new_update)):
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

def main():
    """ Main function """
    power_supplies = {}
    for i in range(1, 3):
        power_supplies[i] = cpx.CPX400DPDriver(i, interface='lan',
                                               hostname='cinf-palle-heating-ps',
                                               tcp_port=9221)
        power_supplies[i].set_voltage(0)
        power_supplies[i].output_status(True)

    codenames = ['setpoint', 'wanted_voltage', 'actual_voltage_1', 'actual_voltage_2',
                 'actual_current_1', 'actual_current_2', 'power', 'temperature']
    pullsocket = DateDataPullSocket('palle_temp_control', codenames,
                                    timeouts=[999999, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0])
    pullsocket.start()

    pushsocket = DataPushSocket('mgw_push_control', action='store_last')
    pushsocket.start()

    power_calculator = PowerCalculatorClass(pullsocket, pushsocket)
    power_calculator.daemon = True
    power_calculator.start()

    heater = HeaterClass(power_calculator, pullsocket, power_supplies)
    heater.start()

    tui = CursesTui(heater)
    tui.daemon = True
    tui.start()

if __name__ == '__main__':
    main()
