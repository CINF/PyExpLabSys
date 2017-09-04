""" Pressure logger, TOF """
from __future__ import print_function
import threading
import time
import logging
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.xgs600 as xgs600
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class PressureReader(threading.Thread):
    """ Pressure reader """
    def __init__(self, xgs):
        threading.Thread.__init__(self)
        self.xgs = xgs
        self.main_chamber = None
        self.flight_tube = None
        self.roughing = None
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
                return_val = self.flight_tube
            if channel == 1:
                return_val = self.main_chamber
            if channel == 2:
                return_val = self.roughing
        return return_val

    def run(self):
        while not self.quit:
            press = self.xgs.read_all_pressures()
            try:
                if not self.quit:
                    self.flight_tube = press[0]
                    self.main_chamber = press[1]
                    self.roughing = press[2]
                    self.ttl = 50
            except IndexError:
                print("av")
            time.sleep(1)

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)
    ports = '/dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0'
    xgs_instance = xgs600.XGS600Driver(ports)
    print(xgs_instance.read_all_pressures())

    pressure = PressureReader(xgs_instance)
    pressure.start()

    time.sleep(2.5)

    codenames = ['tof_iongauge_ft', 'tof_iongauge_main', 'tof_pirani_roughing']
    loggers = {}
    loggers[codenames[0]] = ValueLogger(pressure, comp_val=0.1,
                                        low_comp=1e-11, comp_type='log', channel=0)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(pressure, low_comp=1e-11, comp_val=0.1, comp_type='log', channel=1)
    loggers[codenames[1]].start()
    loggers[codenames[2]] = ValueLogger(pressure, comp_val=0.1, comp_type='log', channel=2)
    loggers[codenames[2]].start()

    livesocket = LiveSocket('TOF data logger', codenames)
    livesocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_tof',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    while pressure.isAlive():
        time.sleep(0.5)
        for name in codenames:
            value = loggers[name].read_value()
            livesocket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(value)
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
