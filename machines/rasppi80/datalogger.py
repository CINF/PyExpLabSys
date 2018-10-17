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
python2_and_3(__file__)
import credentials

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
            for n in range(10):
                try:
                    self.humidity, self.temperature = self.honeywell.read_values()
                    break
                except OSError:
                    time.sleep(5)
            else:
                raise RuntimeError("Ran out of retries")

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    hih_instance = honeywell_6000.HIH6130()
    reader = Reader(hih_instance)
    reader.start()

    time.sleep(5)

    codenames = ['b311_lounge_temperature', 'b311_lounge_humidity']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(reader, comp_val=1, comp_type='lin', channel=1)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(reader, comp_val=1, comp_type='lin', channel=2)
    loggers[codenames[1]].start()

    livesocket = LiveSocket('B311 lounge Air Logger', codenames)
    livesocket.start()

    socket = DateDataPullSocket('B311 Lounge Air Logger', codenames,
                                timeouts=[1.0] * len(loggers))
    socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_b311',
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
                print(value)
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    while True:
        try:
            main()
        except KeyboardInterrupt:
            print("Quitting")
            break
        except OSError as exception:  # Network error
            print("Got '{}'. Wait 5 min and restart".format(exception))
            time.sleep(300)
