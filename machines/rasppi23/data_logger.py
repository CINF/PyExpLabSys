""" Data logger for mobile gas wall """

import threading
import logging
import time
from datetime import datetime

import FindSerialPorts
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataSocket
from PyExpLabSys.common.sockets import LiveSocket
import PyExpLabSys.drivers.xgs600 as xgs600
import credentials


class PressureReader(threading.Thread):
    def __init__(self, xgs_instance):
        threading.Thread.__init__(self)
        self.xgs = xgs_instance
        self.chamberpressure = -9999
        self.bufferpressure = -9999
        self.quit = False

    def run(self):
        while not self.quit:
            time.sleep(1)
            pressures = self.xgs.read_all_pressures()
            self.chamberpressure = pressures[0]
            self.bufferpressure = pressures[1]


class PressureLogger(threading.Thread):
    """ Read a specific XGS pressure """
    def __init__(self, xgsreader, channel):
        threading.Thread.__init__(self)
        self.xgsreader = xgsreader
        self.channel = channel
        self.pressure = None
        self.bufferpressure = None
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False

    def read_pressure(self):
        """ Read the pressure """
        return(self.pressure)

    def run(self):
        while not self.quit:
            time.sleep(2.5)
            if self.channel == 0:
                self.pressure = self.xgsreader.chamberpressure
            if self.channel == 1:
                self.pressure = self.xgsreader.bufferpressure
            time_trigged = (time.time() - self.last_recorded_time) > 600
            val_trigged = not (self.last_recorded_value * 0.9 < self.pressure < self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged) and (self.pressure > 0):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.pressure


if __name__ == '__main__':
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    ports = FindSerialPorts.find_ports()
    for port in ports:
        print port
        xgs = xgs600.XGS600Driver('/dev/' + port)
        if len(xgs.read_software_version()) > 0:
            break

    print xgs.read_all_pressures()

    reader = PressureReader(xgs)
    reader.daemon = True
    reader.start()

    chamber_logger = PressureLogger(reader, 0)
    buffer_logger = PressureLogger(reader, 1)
    chamber_logger.start()
    buffer_logger.start()

    socket = DateDataSocket(['chamber_pressure', 'buffer_pressure'], timeouts=[1.0, 1.0])
    socket.start()

    livesocket = LiveSocket(['chamber_pressure', 'buffer_pressure'], 2)
    livesocket.start()

    db_logger = ContinuousLogger(table='dateplots_mgw', username=credentials.user, password=credentials.passwd, measurement_codenames=['mgw_pressure_chamber', 'mgw_pressure_buffer'])
    db_logger.start()
    time.sleep(5)
    while True:
        c = chamber_logger.read_pressure()
        b = buffer_logger.read_pressure()
        socket.set_point_now('chamber_pressure', c)
        socket.set_point_now('buffer_pressure', b)
        livesocket.set_point_now('chamber_pressure', c)
        livesocket.set_point_now('buffer_pressure', b)

        if chamber_logger.trigged:
            print(c)
            db_logger.enqueue_point_now('mgw_pressure_chamber', c)
            chamber_logger.trigged = False

        if buffer_logger.trigged:
            print(b)
            db_logger.enqueue_point_now('mgw_pressure_buffer', b)
            buffer_logger.trigged = False

