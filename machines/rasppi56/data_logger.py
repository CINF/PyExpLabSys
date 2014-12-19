""" Pressure and temperature logger """
# pylint: disable=C0301,R0904, C0103

import threading
import time
import logging
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.sockets import LiveSocket
import PyExpLabSys.drivers.omega_D6400 as omega_D6400
import credentials

class BaratronClass(threading.Thread):
    """ Pressure reader """
    def __init__(self):
        threading.Thread.__init__(self)
        port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWE9PXJ-if00-port0'
        self.baratron = omega_D6400.OmegaD6400(address=1, port=port)
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
            time.sleep(0.5)
            self.pressure = self.baratron.read_value(1)
            time_trigged = (time.time() - self.last_recorded_time) > 120
            val_trigged = not (self.last_recorded_value * 0.9 < self.pressure < self.last_recorded_value * 1.1)
            if self.pressure < 0.01:
                val_trigged = False
            if (time_trigged or val_trigged):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.pressure

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

pressure_measurement = BaratronClass()
pressure_measurement.deamon = True
pressure_measurement.start()

time.sleep(2)

datasocket = DateDataPullSocket('stm312_hpc_baratron', ['stm312_hpc_baratron'], timeouts=[1.0])
datasocket.start()

db_logger = ContinuousLogger(table='dateplots_stm312', username=credentials.user, password = credentials.passwd, measurement_codenames=['stm312_hpc_baratron'])
db_logger.start()

while True:
    try:
        time.sleep(1)
        baratron = pressure_measurement.read_pressure()
        datasocket.set_point_now('stm312_hpc_baratron', baratron)
        if pressure_measurement.trigged:
            print(baratron)
            db_logger.enqueue_point_now('stm312_hpc_baratron', baratron)
            pressure_measurement.trigged = False
    except KeyboardInterrupt:
        #pressure_measurement.stop()
        datasocket.stop()
        db_logger.stop()
