""" Data logger for the furnaceroom, 307 """

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
            time.sleep(0.1)
            self.temperature = self.comm.read_register(4096, 1)


def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    datasocket = DateDataPullSocket('furnaceroom_reader',
                                    ['T1', 'T2', 'S1', 'S2'],
                                    timeouts=[3.0, 3.0, 9999999, 99999999], port=9001)
    datasocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_furnaceroom307',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=['fr307_furnace_1_T',
                                                           'fr307_furnace_2_T'])

    ports = {}
    ports[1] = 'usb-FTDI_USB-RS485_Cable_FTWGRL9C-if00-port0'
    ports[2] = 'usb-FTDI_USB-RS485_Cable_FTWGRN2W-if00-port0'
    furnaces = {}
    loggers = {}
    for i in [1, 2]:
        furnaces[i] = TemperatureReader(ports[i])
        furnaces[i].daemon = True
        furnaces[i].start()
        loggers[i] = ValueLogger(furnaces[i], comp_val=0.2)
        loggers[i].start()

    db_logger.start()
    time.sleep(5)
    values = {}
    while True:
        time.sleep(0.1)
        for i in [1, 2]:
            values[i] = loggers[i].read_value()
            datasocket.set_point_now('T' + str(i), values[i])
            if loggers[i].read_trigged():
                print('Furnace: ' + str(i) + ': ' + str(values[i]))
                db_logger.save_point_now('fr307_furnace_' + str(i) + '_T', values[i])
                loggers[i].clear_trigged()


if __name__ == '__main__':
    main()
