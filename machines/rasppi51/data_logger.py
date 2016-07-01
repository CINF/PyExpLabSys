""" Pressure and temperature logger, PVD309"""
from __future__ import print_function
import threading
import time
import logging
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.xgs600 as xgs600
import credentials

class XgsReader(threading.Thread):
    """ Pressure reader """
    def __init__(self, xgs):
        threading.Thread.__init__(self)
        self.xgs = xgs
        self.pressures = {}
        self.pressures['ig_ll'] = None # Iog Gauge, Load Lock
        self.pressures['p_r_ll'] = None # Pirani, roughing, turbo, Load Lock
        self.pressures['p_ll'] = None # Pirani, Load Lock
        self.pressures['ig_mc'] = None # Ion gauge, main chamber
        self.pressures['p_r_cr'] = None # Pirani, roughing, cryo pump
        self.pressures['p_mc'] = None # Pirani, main chamber
        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel == 0:
                return_val = self.pressures['ig_ll']
            if channel == 1:
                return_val = self.pressures['p_r_ll']
            if channel == 2:
                return_val = self.pressures['p_ll']
            if channel == 3:
                return_val = self.pressures['ig_mc']
            if channel == 4:
                return_val = self.pressures['p_r_cr']
            if channel == 5:
                return_val = self.pressures['p_mc']
        return return_val

    def run(self):
        while not self.quit:

            time.sleep(0.5)
            press = self.xgs.read_all_pressures()
            try:
                self.ttl = 50
                self.pressures['ig_ll'] = press[0]
                self.pressures['p_r_ll'] = press[1]
                self.pressures['p_ll'] = press[2]
                self.pressures['ig_mc'] = press[3]
                self.pressures['p_r_cr'] = press[4]
                self.pressures['p_mc'] = press[5]
            except IndexError:
                print("av")

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    xgs_port = '/dev/serial/by-id/'
    xgs_port += 'usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
    xgs_instance = xgs600.XGS600Driver(xgs_port)
    print(xgs_instance.read_all_pressures())

    xgs_pressure = XgsReader(xgs_instance)
    xgs_pressure.start()

    time.sleep(2.5)

    codenames = ['pvd309_load_lock_ig', 'pvd309_load_lock_turbo_roughing',
                 'pvd309_load_lock_pirani', 'pvd309_main_chamber_ig',
                 'pvd309_cryo_roughing', 'pvd309_main_chamber_pirani']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(xgs_pressure, comp_val=0.1,
                                        low_comp=1e-9, comp_type='log', channel=0)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(xgs_pressure, comp_val=0.1,
                                        low_comp=1e-3, comp_type='log', channel=1)
    loggers[codenames[1]].start()
    loggers[codenames[2]] = ValueLogger(xgs_pressure, comp_val=0.1,
                                        low_comp=1e-3, comp_type='log', channel=2)
    loggers[codenames[2]].start()
    loggers[codenames[3]] = ValueLogger(xgs_pressure, comp_val=0.1,
                                        low_comp=1e-9, comp_type='log', channel=3)
    loggers[codenames[3]].start()
    loggers[codenames[4]] = ValueLogger(xgs_pressure, comp_val=0.3,
                                        low_comp=1e-2, comp_type='log', channel=4)
    loggers[codenames[4]].start()
    loggers[codenames[5]] = ValueLogger(xgs_pressure, comp_val=0.1,
                                        low_comp=1e-3, comp_type='log', channel=5)
    loggers[codenames[5]].start()

    livesocket = LiveSocket('pvd309 pressure logger', codenames)
    livesocket.start()

    socket = DateDataPullSocket('pvd309 pressure', codenames, timeouts=[1.0]*6)
    socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_pvd309',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    while xgs_pressure.isAlive():
        time.sleep(0.25)
        for name in codenames:
            value = loggers[name].read_value()
            livesocket.set_point_now(name, value)
            socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print (name + ': ' + str(value))
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
