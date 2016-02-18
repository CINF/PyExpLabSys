""" Pressure and temperature logger """
# pylint: disable=C0301,R0904, C0103
from __future__ import print_function
import threading
import time
import logging
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.xgs600 as xgs600
import PyExpLabSys.drivers.agilent_34972A as agilent_34972A


class MuxReader(threading.Thread):
    """ Analog reader """
    def __init__(self, mux):
        threading.Thread.__init__(self)
        self.mux = mux
        self.ttl = 20
        self.temperature = None
        self.quit = False

    def value(self):
        """ Read the temperaure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        return(self.temperature)

    def run(self):
        while not self.quit:
            self.ttl = 20
            time.sleep(1)
            mux_list = self.mux.read_single_scan()
            self.temperature = mux_list[0]

class PressureReader(threading.Thread):
    """ Pressure reader """
    def __init__(self, xgs):
        threading.Thread.__init__(self)
        self.xgs = xgs
        self.pressure = None
        self.quit = False
        self.ttl = 20

    def value(self):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        return(self.pressure)

    def run(self):
        while not self.quit:
            self.ttl = 20
            time.sleep(0.5)
            press = self.xgs.read_all_pressures()
            try:
                self.pressure = press[0]
            except IndexError:
                print("av")
                self.pressure = 0

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

mux_instance = agilent_34972A.Agilent34972ADriver('volvo-agilent-34972a')
#mux_instance = agilent_34972A.Agilent34972ADriver('10.54.6.144')
xgs_instance = xgs600.XGS600Driver('/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0')

analog_measurement = MuxReader(mux_instance)
analog_measurement.start()

pressure = PressureReader(xgs_instance)
pressure.start()

time.sleep(2.5)

codenames = ['volvo_pressure', 'volvo_temperature']
loggers = {}
loggers[codenames[0]] = ValueLogger(pressure, comp_val = 0.1, comp_type = 'log')
loggers[codenames[0]].start()
loggers[codenames[1]] = ValueLogger(analog_measurement, comp_val = 0.5, comp_type = 'lin')
loggers[codenames[1]].start()

socket = DateDataPullSocket('Volvo data logger', codenames, timeouts=[1.0, 1.0])
socket.start()

livesocket = LiveSocket('Volvo data logger', codenames, 2)
livesocket.start()

db_logger = ContinuousLogger(table='dateplots_volvo', username='volvo', password='volvo', measurement_codenames=['volvo_pressure', 'volvo_temperature'])
db_logger.start()

while pressure.isAlive() and analog_measurement.isAlive():
    time.sleep(0.25)
    for name in codenames:
        v = loggers[name].read_value()
        socket.set_point_now(name, v)
        livesocket.set_point_now(name, v)
        if loggers[name].read_trigged():
            print(v)
            db_logger.enqueue_point_now(name, v)
            loggers[name].clear_trigged()
