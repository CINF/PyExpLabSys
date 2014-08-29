""" Data logger for muffle furnace, chemlab 307 """
# pylint: disable=C0301,R0904, C0103

import threading
import logging
import time
import minimalmodbus
import serial
from PyExpLabSys.common.loggers import ContinuousLogger
import credentials


class TemperatureReader(threading.Thread):
    """ Communicates with the Omega ?? """
    def __init__(self):
        self.f = minimalmodbus.Instrument('/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWE9XWB-if00-port0', 1)
        self.f.serial.baudrate = 9600
        self.f.serial.parity = serial.PARITY_EVEN
        self.f.serial.timeout = 0.25
        threading.Thread.__init__(self)
        self.temperature = 0
        self.quit = False

    def run(self):
        while not self.quit:
            self.temperature = self.f.read_register( 4096, 1)


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
            time.sleep(2.5)
            self.value = self.tempreader.temperature
            time_trigged = (time.time() - self.last_recorded_time) > self.maximumtime
            val_trigged = not (self.last_recorded_value - 1 < self.value < self.last_recorded_value + 1)
            if (time_trigged or val_trigged):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.value

if __name__ == '__main__':
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    tempreader = TemperatureReader()
    tempreader.daemon = True
    tempreader.start()

    temp_logger = TemperatureLogger(tempreader)
    temp_logger.start()

    db_logger = ContinuousLogger(table='dateplots_chemlab307',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=['chemlab307_muffle_furnace'])
    db_logger.start()
    time.sleep(5)
    while True:
        time.sleep(0.25)
        t = temp_logger.read_value()
        if temp_logger.trigged:
            print t
            db_logger.enqueue_point_now('chemlab307_muffle_furnace', t)
            temp_logger.trigged = False
