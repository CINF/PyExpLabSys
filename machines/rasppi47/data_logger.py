""" Data logger for the furnaceroom, 307 """
from __future__ import print_function
import threading
import logging
import time
import minimalmodbus
import serial
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)


class TemperatureReader(threading.Thread):
    """ Communicates with the Omega ?? """
    def __init__(self, port):
        self.comm = minimalmodbus.Instrument('/dev/serial/by-id/' + port, 1)
        self.comm.serial.baudrate = 9600
        self.comm.serial.parity = serial.PARITY_EVEN
        self.comm.serial.timeout = 0.5
        self.temperature = -999
        threading.Thread.__init__(self)
        self.quit = False

    def value(self):
        """ Return current temperature """
        return self.temperature

    def run(self):
        while not self.quit:
            time.sleep(1)
            self.temperature = self.comm.read_register(4096, 1)

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    codenames = ['fr307_furnace_1_T', 'fr307_furnace_2_T']

    datasocket = DateDataPullSocket('furnaceroom_reader', codenames,
                                    timeouts=[3.0, 3.0], port=9001)
    datasocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_furnaceroom307',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    ports = {}
    ports['fr307_furnace_1_T'] = 'usb-FTDI_USB-RS485_Cable_FTWGRL9C-if00-port0'
    ports['fr307_furnace_2_T'] = 'usb-FTDI_USB-RS485_Cable_FTWGRN2W-if00-port0'
    loggers = {}
    temperature_readers = {}
    for logger_name in codenames:
        temperature_readers[logger_name] = TemperatureReader(ports[logger_name])
        temperature_readers[logger_name].daemon = True
        temperature_readers[logger_name].start()
        loggers[logger_name] = ValueLogger(temperature_readers[logger_name], comp_val=0.09)
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
