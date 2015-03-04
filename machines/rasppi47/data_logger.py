""" Data logger for the furnaceroom, 307 """
# pylint: disable=C0301,R0904, C0103

import threading
import logging
import time
import minimalmodbus
import serial
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
import credentials


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

    def run(self):
        while not self.quit:
            time.sleep(0.1)
            self.temperature = self.comm.read_register(4096, 1)


class TemperatureLogger(threading.Thread):
    """ Read a specific temperature """
    def __init__(self, tempreader, maximumtime=600):
        threading.Thread.__init__(self)
        self.tempreader = tempreader
        self.value = None
        self.maximumtime = maximumtime
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False

    def read_value(self):
        """ Read the temperature """
        return(self.value)

    def run(self):
        while not self.quit:
            time.sleep(0.5)
            self.value = self.tempreader.temperature
            time_trigged = (time.time() - self.last_recorded_time) > self.maximumtime
            val_trigged = not (self.last_recorded_value - 0.3 < self.value < self.last_recorded_value + 0.3)
            if (time_trigged or val_trigged):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.value

if __name__ == '__main__':
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    datasocket = DateDataPullSocket('furnaceroom_reader',
                                    ['T1', 'T2', 'S1', 'S2'],
                                    timeouts=[3.0, 3.0, 9999999, 99999999], port=9001)
    datasocket.start()

    db_logger = ContinuousLogger(table='dateplots_furnaceroom307',
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
        print i
        furnaces[i] = TemperatureReader(ports[i])
        furnaces[i].daemon = True
        furnaces[i].start()
        loggers[i] = TemperatureLogger(furnaces[i])
        loggers[i].start()

    db_logger.start()
    time.sleep(5)
    values = {}
    while True:
        time.sleep(0.1)
        for i in [1, 2]:
            values[i] = loggers[i].read_value()
            datasocket.set_point_now('T' + str(i), values[i])
            if loggers[i].trigged:
                print 'Furnace: ' + str(i) + ': ' + str(values[i])
                db_logger.enqueue_point_now('fr307_furnace_' + str(i) + '_T', values[i])
                loggers[i].trigged = False
