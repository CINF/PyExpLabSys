""" Data logger for mobile gas wall """
# pylint: disable=C0301,R0904, C0103

import threading
import logging
import time
import FindSerialPorts
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.sockets import LiveSocket
import PyExpLabSys.drivers.xgs600 as xgs600
import credentials


class PressureReader(threading.Thread):
    """ Communicates with the XGS controller """
    def __init__(self, xgs_instance):
        threading.Thread.__init__(self)
        self.xgs = xgs_instance
        self.pressures = self.xgs.read_all_pressures()
        self.quit = False

    def run(self):
        while not self.quit:
            time.sleep(2)
            self.pressures = self.xgs.read_all_pressures()


class PressureLogger(threading.Thread):
    """ Read a specific XGS pressure """
    def __init__(self, xgsreader, channel, maximumtime=600):
        threading.Thread.__init__(self)
        self.xgsreader = xgsreader
        self.channel = channel
        self.pressure = None
        self.maximumtime = maximumtime
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = True

    def read_pressure(self):
        """ Read the pressure """
        return(self.pressure)

    def run(self):
        while not self.quit:
            time.sleep(1)
            self.pressure = self.xgsreader.pressures[self.channel]
            time_trigged = (time.time() - self.last_recorded_time) > self.maximumtime
            val_trigged = not (self.last_recorded_value * 0.9 < self.pressure < self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged) and (self.pressure > 0):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.pressure


if __name__ == '__main__':
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    xgs = xgs600.XGS600Driver('/dev/ttyUSB1')

    print xgs.read_all_pressures()

    pressurereader = PressureReader(xgs)
    pressurereader.daemon = True
    pressurereader.start()

    pressure_codenames = ['pvd309_main_chamber_ig',
                          'pvd309_main_chamber_pirani',
                          'pvd309_load_lock_pirani']
    loggers = {}
    loggers['pvd309_main_chamber_ig'] = PressureLogger(pressurereader, 3)
    loggers['pvd309_main_chamber_pirani'] = PressureLogger(pressurereader, 2)
    loggers['pvd309_load_lock_pirani'] = PressureLogger(pressurereader, 5)

    for codename in pressure_codenames:
        loggers[codename].start()

    socket = DateDataPullSocket('pvd309', pressure_codenames, timeouts=[5.0, 5.0, 5.0])
    socket.start()

    db_logger = ContinuousLogger(table='dateplots_pvd309',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=pressure_codenames)
    db_logger.start()

    time.sleep(3)

    while True:
        time.sleep(0.25)
        for codename in pressure_codenames:
            p = loggers[codename].read_pressure()
            socket.set_point_now(codename, p)
            if loggers[codename].trigged:
                print p
                db_logger.enqueue_point_now(codename, p)
                loggers[codename].trigged = False


