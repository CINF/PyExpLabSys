""" Data logger for muffle furnace, chemlab 307 """
# pylint: disable=C0301,R0904, C0103

import threading
import logging
import time
import minimalmodbus
import serial
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
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

    def value(self):
        return self.temperature

    def run(self):
        while not self.quit:
            time.sleep(0.2)
            self.temperature = self.f.read_register(4096, 1)


if __name__ == '__main__':
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    tempreader = TemperatureReader()
    tempreader.daemon = True
    tempreader.start()

    temp_logger = ValueLogger(tempreader, comp_val=1)
    #temp_logger = TemperatureLogger(tempreader)
    temp_logger.start()

    db_logger = ContinuousLogger(table='dateplots_chemlab307',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=['chemlab307_muffle_furnace'])

    socket = DateDataPullSocket('muffle_furnace',
                                ['chemlab307_muffle_furnace'],
                                timeouts=[1.0])
    socket.start()

    livesocket = LiveSocket('muffle_furnace', ['chemlab307_muffle_furnace'], 2)
    livesocket.start()

    db_logger.start()
    time.sleep(5)
    while True:
        time.sleep(0.25)
        t = temp_logger.read_value()
        socket.set_point_now('chemlab307_muffle_furnace', t)
        livesocket.set_point_now('chemlab307_muffle_furnace', t)
        if temp_logger.read_trigged():
            print t
            db_logger.enqueue_point_now('chemlab307_muffle_furnace', t)
            temp_logger.clear_trigged()
