# pylint: disable=R0913,W0142,C0103

""" Temperature controller """
import time
import threading
import socket
import PyExpLabSys.auxiliary.pid as PID
import PyExpLabSys.drivers.cpx400dp as cpx
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
import temperature_tui

class PowerCalculatorClass(threading.Thread):
    """ Calculate the wanted amount of power """
    def __init__(self, pullsocket, pushsocket, data_command, pid_params):
        threading.Thread.__init__(self)
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.power = 0
        self.setpoint = 0
        self.pid = PID.PID(pid_p=pid_params[0], pid_i=pid_params[1], p_max=pid_params[2])
        self.update_setpoint(self.setpoint)
        self.quit = False
        self.temperature = None
        self.temp_command = data_command

    def read_power(self):
        """ Return the calculated wanted power """
        return(self.power)

    def update_setpoint(self, setpoint):
        """ Update the setpoint """
        self.setpoint = setpoint
        self.pid.update_setpoint(setpoint)
        self.pullsocket.set_point_now('setpoint', setpoint)
        return setpoint

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        sp_updatetime = 0
        while not self.quit:
            sock.sendto(self.temp_command, ('localhost', 9001))
            received = sock.recv(1024)
            self.temperature = float(received[received.find(',') + 1:])
            self.power = self.pid.wanted_power(self.temperature)

            #  Handle the setpoint from the network
            try:
                setpoint = self.pushsocket.last[1]['setpoint']
                new_update = self.pushsocket.last[0]
            except (TypeError, KeyError): #  Setpoint has never been sent
                setpoint = None
            if ((setpoint is not None) and
                (setpoint != self.setpoint) and (sp_updatetime < new_update)):
                self.update_setpoint(setpoint)
                sp_updatetime = new_update
            time.sleep(1)

class CommonPowerSupply(threading.Thread):
    """ Share a power supply """
    def __init__(self):
        threading.Thread.__init__(self)
        port = '/dev/serial/by-id/usb-TTI_CPX400_Series_PSU_5512626F-if00'
        self.mai = cpx.CPX400DPDriver(1, interface='serial', device=port)
        self.dca = cpx.CPX400DPDriver(2, interface='serial', device=port)
        self.dca.set_current_limit(7)
        self.mai.set_current_limit(11)
        self.voltage = {}
        self.voltage['mai'] = 0
        self.voltage['dca'] = 0
        self.dca.output_status(True)
        self.mai.output_status(True)
        self.actual_voltage = {}
        self.actual_current = {}
        self.actual_voltage['mai'] = 0
        self.actual_current['mai'] = 0
        self.actual_voltage['dca'] = 0
        self.actual_current['dca'] = 0
        self.quit = False

    def run(self):
        while not self.quit:
            time.sleep(0.2)
            self.actual_voltage['mai'] = self.mai.read_actual_voltage()
            self.actual_voltage['dca'] = self.dca.read_actual_voltage()
            self.actual_current['mai'] = self.mai.read_actual_current()
            self.actual_current['dca'] = self.dca.read_actual_current()
            self.dca.set_voltage(self.voltage['dca'])
            self.mai.set_voltage(self.voltage['mai'])
        self.dca.set_voltage(0)
        self.mai.set_voltage(0)
        self.dca.output_status(False)
        self.mai.output_status(False)


class HeaterClass(threading.Thread):
    """ Do the actual heating """
    def __init__(self, power_calculator, pullsocket, ps, ps_name):
        threading.Thread.__init__(self)
        self.pc = power_calculator
        self.pullsocket = pullsocket
        self.ps = ps
        self.ps_name = ps_name
        self.voltage = 0
        self.actual_voltage = 0
        self.current = 0
        self.quit = False

    def run(self):
        while not self.quit:
            self.voltage = self.pc.read_power()
            self.current = self.ps.actual_current[self.ps_name]
            self.actual_voltage = self.ps.actual_voltage[self.ps_name]
            self.pullsocket.set_point_now('voltage', self.voltage)
            self.ps.voltage[self.ps_name] = self.voltage
            time.sleep(0.25)
        self.ps.voltage[self.ps_name] = 0
        self.ps.quit = True

PS = CommonPowerSupply()
PS.start()

Pullsocket_mai = DateDataPullSocket('pvd_temp_control_mai', ['setpoint', 'voltage'], 
                                    timeouts=[999999, 3], port=9000)
Pullsocket_mai.start()
Pullsocket_dca = DateDataPullSocket('pvd_temp_control_dca', ['setpoint', 'voltage'], 
                                    timeouts=[999999, 3], port=9002)
Pullsocket_dca.start()

Pushsocket_mai = DataPushSocket('pvd309_push_control_mai', action='store_last', port=8500)
Pushsocket_mai.start()
Pushsocket_dca = DataPushSocket('pvd309_push_control_dca', action='store_last', port=8502)
Pushsocket_dca.start()

Pid_Params = [0.6, 0.0035, 5]
P_mai = PowerCalculatorClass(Pullsocket_mai, Pushsocket_mai,
                             'pvd309_temp_mai_cell#raw', pid_params=Pid_Params)
P_mai.daemon = True
P_mai.start()

Pid_Params = [0.2, 0.001, 9]
P_dca = PowerCalculatorClass(Pullsocket_dca, Pushsocket_dca,
                             'pvd309_temp_dca_cell#raw', pid_params=Pid_Params)
P_dca.daemon = True
P_dca.start()

H_mai = HeaterClass(P_mai, Pullsocket_mai, PS, 'mai')
H_mai.start()

H_dca = HeaterClass(P_dca, Pullsocket_dca, PS, 'dca')
H_dca.start()

Heaters = {}
Heaters[0] = H_mai
Heaters[1] = H_dca

T = temperature_tui.CursesTui(Heaters)
T.daemon = True
T.start()
