""" Pressure and temperature logger """
from __future__ import print_function
import threading
import time
import logging
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.omron_d6fph as omron_d6fph
import PyExpLabSys.drivers.honeywell_6000 as honeywell_6000
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class Reader(threading.Thread):
    """ Pressure reader """
    def __init__(self, omron, honeywell):
        threading.Thread.__init__(self)
        self.omron = omron
        self.honeywell = honeywell
        self.pressure = None
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
            if channel == 0:
                return_val = self.pressure
            if channel == 1:
                return_val = self.temperature
            if channel == 2:
                return_val = self.humidity
        return return_val

    def run(self):
        while not self.quit:
            pressures = []
            self.ttl = 50
            t = time.time()
            for _ in range(0, 50):
                pressure = self.omron.read_pressure()
                pressures.append(pressure)
            self.pressure = sum(pressures) / len(pressures)
            self.humidity, self.temperature = self.honeywell.read_values()
            print(time.time() - t)


def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    omron_instance = omron_d6fph.OmronD6fph()
    hih_instance = honeywell_6000.HIH6130()
    reader = Reader(omron_instance, hih_instance)
    reader.start()

    time.sleep(5)

    codenames = ['hall_ventilation_pressure', 'hall_temperature', 'hall_humidity']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(reader, comp_val=1.0, maximumtime=300,
                                        comp_type='lin', channel=0)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(reader, comp_val=0.2, maximumtime=600,
                                        comp_type='lin', channel=1)
    loggers[codenames[1]].start()
    loggers[codenames[2]] = ValueLogger(reader, comp_val=0.2, maximumtime=600,
                                        comp_type='lin', channel=2)
    loggers[codenames[2]].start()

    livesocket = LiveSocket('Hall Ventilation Logger', codenames)
    livesocket.start()

    socket = DateDataPullSocket('Hall Ventilation logger', codenames,
                                timeouts=[1.0] * len(loggers))
    socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_hall',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    while reader.isAlive():
        time.sleep(1)
        for name in codenames:
            value = loggers[name].read_value()
            livesocket.set_point_now(name, value)
            socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(name + ': ' + str(value))
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    while True:
        try:
            main()
        except OSError as exception:
            print("Got '{}'. Wait 10 min and restart.".format(exception))
            time.sleep(600)
        except KeyboardInterrupt:
            print("Quitting")
            break
