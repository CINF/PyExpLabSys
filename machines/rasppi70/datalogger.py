""" Pressure and temperature logger """
from __future__ import print_function
import threading
import time
import logging
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.honeywell_6000 as honeywell_6000
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class Reader(threading.Thread):
    """ Pressure reader """
    def __init__(self, honeywell):
        threading.Thread.__init__(self)
        self.honeywell = honeywell
        self.temperature = None
        self.humidity = None
        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read temperature and  pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel == 1:
                return_val = self.temperature
            if channel == 2:
                return_val = self.humidity
        return return_val

    def run(self):
        while not self.quit:
            self.ttl = 50
            self.humidity, self.temperature = self.honeywell.read_values()

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    hih_instance = honeywell_6000.HIH6130()
    reader = Reader(hih_instance)
    reader.daemon = True
    reader.start()

    time.sleep(5)

    codenames = ['chemlab312_temperature', 'chemlab312_humidity']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(reader, comp_val=0.2, comp_type='lin', channel=1)
    loggers[codenames[0]].daemon = True
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(reader, comp_val=0.2, comp_type='lin', channel=2)
    loggers[codenames[1]].daemon = True
    loggers[codenames[1]].start()

    livesocket = LiveSocket('Chemlab312 Air Logger', codenames)
    livesocket.start()

    socket = DateDataPullSocket('Chemlab312 Air Logger', codenames,
                                timeouts=[1.0] * len(loggers))
    socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_chemlab312',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    while reader.isAlive():
        time.sleep(0.5)
        for name in codenames:
            value = loggers[name].read_value()
            livesocket.set_point_now(name, value)
            socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(value)
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
