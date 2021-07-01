""" Data logger for heating block on VHP alkali doser """
from __future__ import print_function
import threading
import logging
import time
import minimalmodbus
import serial
from PyExpLabSys.drivers.omega_cn7800 import CN7800
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)


class TemperatureReader(threading.Thread):
    """ Communicates with the Omega ?? """
    def __init__(self, omega):
        threading.Thread.__init__(self)
        self.omega = omega
        self.temperature = None
        self.quit = False
        self.ttl = 20
        
    def value(self,channel=None):
        self.ttl -= 1
        if self.ttl <= 0:
            self.quit = True
            return_val = None
        else:
            return_val = self.temperature
        return return_val        
    
    def run(self):
        try:
            while not self.quit:
                self.ttl = 50
                self.temperature = self.omega.read_temperature()
        except ValueError:
            self.temperature = None
            self.ttl -= 1
            print("Check if omega has power")
        finally:
            self.quit = True
def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    codenames = ['vhp_T_jacket']

    datasocket = DateDataPullSocket('VHP_T_jacket_reader', codenames,
                                    port=9001)
    datasocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_vhp_setup',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    ports = {}
    ports['vhp_T_jacket'] = 'usb-FTDI_USB-RS485_Cable_FT1F9WC2-if00-port0'
    loggers = {}
    temperature_readers = {}
    for logger_name in codenames:
        temperature_readers[logger_name] = TemperatureReader(CN7800(ports[logger_name]))
        temperature_readers[logger_name].daemon = True
        temperature_readers[logger_name].start()
        loggers[logger_name] = ValueLogger(temperature_readers[logger_name], comp_val=1)
        loggers[logger_name].start()

    time.sleep(5)

    values = {}
    while True:
        time.sleep(1)
        for logger_name in codenames:
            values[logger_name] = loggers[logger_name].read_value()
            datasocket.set_point_now(logger_name, values[logger_name])
            if loggers[logger_name].read_trigged():
                print(logger_name + ': ' + str(values[logger_name]))
                db_logger.save_point_now(logger_name, values[logger_name])
                loggers[logger_name].clear_trigged()


if __name__ == '__main__':
    main()
