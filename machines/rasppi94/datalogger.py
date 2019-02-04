""" Temperature and humidity logger """
from __future__ import print_function
import threading
import time
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.honeywell_6000 as honeywell_6000
import PyExpLabSys.common.utilities
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
PyExpLabSys.common.utilities.ERROR_EMAIL = 'robert.jensen@fysik.dtu.dk'
python2_and_3(__file__)

LOGGER = get_logger('GC MS temperature logger', level='WARN', file_log=True,
                    file_name='temp_control.log', terminal_log=False, email_on_warnings=False)

LOGGER.warning('Program started')


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
            try:
                self.humidity, self.temperature = self.honeywell.read_values()
                self.ttl = 50
            except OSError:
                pass

def main():
    """ Main function """
    hih_instance = honeywell_6000.HIH6130()
    reader = Reader(hih_instance)
    reader.start()

    time.sleep(5)

    codenames = ['gc_ms_inner_temperature', 'gc_ms_inner_humidity']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(reader, comp_val=0.1, maximumtime=10,
                                        comp_type='lin', channel=1)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(reader, comp_val=1, maximumtime=10,
                                        comp_type='lin', channel=2)
    loggers[codenames[1]].start()

    socket = DateDataPullSocket('gc_ms_temperature_humidity', codenames,
                                timeouts=[1.0] * len(loggers))
    socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_gc_ms',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    while reader.isAlive():
        time.sleep(1)
        for name in codenames:
            value = loggers[name].read_value()
            socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(value)
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
