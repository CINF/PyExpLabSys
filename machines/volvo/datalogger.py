""" Pressure and temperature logger """
# pylint: disable=C0301,R0904, C0103

import threading
import time
import logging

from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataSocket
import PyExpLabSys.drivers.xgs600 as xgs600
import PyExpLabSys.drivers.agilent_34972A as agilent_34972A


class MuxClass(threading.Thread):
    """ Analog reader """
    def __init__(self):
        threading.Thread.__init__(self)
        self.mux = agilent_34972A.Agilent34972ADriver('volvo-agilent-34972a')
        self.temperature = None
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False

    def read_temperature(self):
        """ Read the temperaure """
        return(self.temperature)

    def run(self):
        while not self.quit:
            time.sleep(1)
            mux_list = self.mux.read_single_scan()
            self.temperature = mux_list[0]
            time_trigged = (time.time() - self.last_recorded_time) > 60
            val_trigged = not ((self.last_recorded_value - 0.5) < self.temperature < (self.last_recorded_value + 0.5))
            if (time_trigged or val_trigged):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.temperature


class XGSClass(threading.Thread):
    """ Pressure reader """
    def __init__(self):
        threading.Thread.__init__(self)
        self.xgs = xgs600.XGS600Driver()
        self.pressure = None
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
            press = self.xgs.read_all_pressures()
            try:
                self.pressure = press[0]
            except IndexError:
                print "av"
                self.pressure = 0
            time_trigged = (time.time() - self.last_recorded_time) > 60
            val_trigged = not (self.last_recorded_value * 0.9 < self.pressure < self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged) and (self.pressure > 0):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.pressure

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

analog_measurement = MuxClass()
analog_measurement.start()

pressure_measurement = XGSClass()
pressure_measurement.start()

time.sleep(2.5)

socket = DateDataSocket(['pressure', 'temperature'], timeouts=[1.0, 1.0])
socket.start()

db_logger = ContinuousLogger(table='dateplots_volvo', username='volvo', password='volvo', measurement_codenames=['volvo_pressure', 'volvo_temperature'])
db_logger.start()

while True:
    p = pressure_measurement.read_pressure()
    t = analog_measurement.read_temperature()
    socket.set_point_now('pressure', p)
    socket.set_point_now('temperature', t)
    if pressure_measurement.trigged:
        print(p)
        db_logger.enqueue_point_now('volvo_pressure', p)
        pressure_measurement.trigged = False

    if analog_measurement.trigged:
        print(t)
        db_logger.enqueue_point_now('volvo_temperature', t)
        analog_measurement.trigged = False
