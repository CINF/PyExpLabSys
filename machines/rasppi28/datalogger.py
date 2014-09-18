""" Pressure and temperature logger """
# pylint: disable=C0301,R0904, C0103

import threading
import time
import logging

from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataSocket
from PyExpLabSys.common.sockets import LiveSocket
import PyExpLabSys.drivers.xgs600 as xgs600

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
                self.pressure = press[1]
            except IndexError:
                print "av"
                self.pressure = 0
            time_trigged = (time.time() - self.last_recorded_time) > 600
            val_trigged = not (self.last_recorded_value * 0.9 < self.pressure < self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged) and (self.pressure > 0):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.pressure

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

pressure_measurement = XGSClass()
pressure_measurement.start()

time.sleep(2.5)

socket = DateDataSocket(['pressure'], timeouts=[1.0])
socket.start()

#livesocket = LiveSocket(['pressure'], 2)
#livesocket.start()

db_logger = ContinuousLogger(table='dateplots_ps', username='PS', password='PS', measurement_codenames=['ps_chamber_pressure'])
db_logger.start()

while True:
    time.sleep(0.25)
    p = pressure_measurement.read_pressure()
    socket.set_point_now('pressure', p)
    #livesocket.set_point_now('pressure', p)
    if pressure_measurement.trigged:
        print(p)
        db_logger.enqueue_point_now('ps_chamber_pressure', p)
        pressure_measurement.trigged = False
