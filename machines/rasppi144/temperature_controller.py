""" Temperature controller for microreactors """
from __future__ import print_function
import time
import threading
import socket
import pickle

import PyExpLabSys.drivers.omegabus as omegabus
import PyExpLabSys.drivers.cpx400dp as cpx
import PyExpLabSys.common.utilities
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.microreactor_temperature_control import HeaterClass
from PyExpLabSys.common.microreactor_temperature_control import CursesTui
from PyExpLabSys.common.utilities import activate_library_logging
from PyExpLabSys.common.supported_versions import python2_and_3
PyExpLabSys.common.utilities.ERROR_EMAIL = 'alexkbb@fysik.dtu.dk'
python2_and_3(__file__)

try:
    MICRO = chr(0x03BC) # Python 3
except ValueError:
    MICRO = unichr(0x03BC) # Python 2

LOGGER = get_logger(MICRO + '-reactor anodic bonding temperature control', level='ERROR', file_log=True,
                    file_name='temp_control.log', terminal_log=False, email_on_warnings=False)
activate_library_logging('PyExpLabSys.common.microreactor_temperature_control',
                         logger_to_inherit_from=LOGGER)
#activate_library_logging('PyExpLabSys.auxiliary.pid', logger_to_inherit_from=LOGGER)

LOGGER.warn('Program started')

class ValueReader(threading.Thread):
    """ Read temperature of anodic bonding setup """
    def __init__(self, omega):                                                            
        threading.Thread.__init__(self)                                                   
        self.omegabus = omega                                                             
        self.ttl = 20                                                                     
        self.temperature = None                                                           
        self.quit = False                                                                 
                                                                                           
    def value(self):                                                                      
        """ Read the temperaure """                                                       
        #self.ttl = self.ttl - 1                                                           
        #if self.ttl < 0:                                                                  
        #    self.quit = True                                                              
        return self.temperature                                                           
                                                                                          
    def run(self):                                                                        
        while not self.quit:                                                              
            self.ttl = 20                                                                 
            time.sleep(1)                                                                 
            self.temperature = self.omegabus.read_value(2) 
        self.stop()

    def stop(self):
        """ Clean up """
        while self.isAlive():
            time.sleep(0.2)

class SetPowerClass(threading.Thread):
    """ Calculate the wanted amount of power """
    def __init__(self, pullsocket, pushsocket, value_reader):
        threading.Thread.__init__(self)
        self.value_reader = value_reader
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.values = {}
        self.values['temperature_bottom'] = -500
        self.values['temperature_top'] = -500
        self.values['voltage'] = 0
        self.values['current'] = 0
        self.values['power'] = 0
        self.values['setpoint'] = -1  # Setpoint is in voltage different frome the microreactor
        self.update_setpoint(self.values['setpoint'])
        self.quit = False
        self.ramp = None

    def read_power(self):
        """ Return the calculated wanted power """
        return self.values['voltage']

    def update_setpoint(self, setpoint=None, ramp=0):
        """ Update the setpoint """
        self.values['setpoint'] = setpoint
        #self.pid.update_setpoint(setpoint)
        self.pullsocket.set_point_now('setpoint', setpoint)
        return setpoint



    def run(self):
        start_time = 0
        sp_updatetime = 0
        ramp_updatetime = 0
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1)
        while not self.quit:
            self.values['temperature_bottom'] = self.value_reader['bottom'].value()
            self.values['temperature_top'] = self.value_reader['top'].value()

            self.pullsocket.set_point_now('mr_bonding_temp_bottom', self.values['temperature_bottom'])
            self.pullsocket.set_point_now('mr_bonding_temp_top', self.values['temperature_top'])
            
            try: 
                self.values['voltage'] = self.values['setpoint']  # Voltage wanted to bonding self.pid.wanted_power(self.values['temperature'])
            except ValueError:
                print('Could not set voltage from setpoint. propably negative')

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

        self.stop()

    def stop(self):
        """ Clean up """
        time.sleep(0.5)

def main():
    """ Main function """
    time.sleep(1)
    port = 'usb-FTDI_USB-RS232_Cable_FT4RUN88-if00-port0'
    omega = omegabus.OmegaBus(device='/dev/serial/by-id/' + port, model='D5321', baud=9600)
    anodic_bottom_reader = ValueReader(omega)
    anodic_bottom_reader.daemon = True
    anodic_bottom_reader.start()

    time.sleep(3)


    port = 'usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
    omega_top = omegabus.OmegaBus(device='/dev/serial/by-id/' + port, model='D5321', baud=9600)
    anodic_top_reader = ValueReader(omega_top)
    anodic_top_reader.daemon = True
    anodic_top_reader.start()
    
    time.sleep(3)

    anodic_temp_reader = {'bottom':anodic_bottom_reader, 
                          'top':anodic_top_reader}
    
    time.sleep(3)
    power_supply = {}
    for k in range(1, 3):
        power_supply[k] = cpx.CPX400DPDriver(k, interface='serial',
                                             device='/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0',
                                             )
        power_supply[k].set_voltage(0)
        power_supply[k].output_status(True)

    codenames = ['setpoint', 'wanted_voltage', 'actual_voltage_1', 'actual_voltage_2',
                 'actual_current_1', 'actual_current_2', 'power_1', 'power_2', 'mr_bonding_temp_bottom', 'mr_bonding_temp_top']
    pullsocket = DateDataPullSocket(MICRO + '-reactorng_temp_control', codenames,
                                    timeouts=[999999, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0])
    pullsocket.start()
    
    pushsocket = DataPushSocket(MICRO + '-reactor_anodic_push_control', action='store_last')
    pushsocket.start()

    power_calculator = SetPowerClass(pullsocket, pushsocket, value_reader=anodic_temp_reader)
    power_calculator.daemon = True
    power_calculator.start()

    heater = HeaterClass(power_calculator, pullsocket, power_supply)
    heater.start()

    tui_class = CursesTui(heater)
    tui_class.start()
    LOGGER.info('script ended')

if __name__ == '__main__':
    main()
