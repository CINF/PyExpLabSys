""" Pressure and temperature logger """
# pylint: disable=C0301,R0904, C0103

import threading
import xgs600
import time

from PyExpLabSys.common.loggers import ContinuousLogger
#from PyExpLabSys.common.sockets import DateDataSocket


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
            self.trigged = (time_trigged or val_trigged) and (self.pressure > 0)
            if self.trigged:
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.pressure

db_logger = ContinuousLogger(table='dateplots_dummy', username='dummy', password='dummy', measurement_codenames=['dummy_sine_one'])
db_logger.start()

#socket = DateDataSocket(['s1m1', 's1m2'], timeouts=[1.0, 0.7])
#socket.start()

pressure_measurement = XGSClass()
pressure_measurement.start()

# Initialize variable for the logging condition
while True:
    if pressure_measurement.trigged:
        db_logger.enqueue_point_now('dummy_sine_one', pressure_measurement.read_pressure())
        pressure_measurement.trigged = False
