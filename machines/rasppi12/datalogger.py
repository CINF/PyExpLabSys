""" Pressure and temperature logger """
# pylint: disable=C0301,R0904, C0103

import threading
import time
import logging
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.omega_cni as omega_CNi32
import credentials

class TempReader(threading.Thread):
    """ Temperature reader """
    def __init__(self, omega):
        threading.Thread.__init__(self)
        self.omega = omega
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
            self.temperature = self.omega.read_temperature()

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

port = 'usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
ng_temp = omega_CNi32.ISeries('/dev/serial/by-id/' + port, 9600)

ng_measurement = TempReader(ng_temp)
ng_measurement.start()

time.sleep(2.5)

codenames = ['microreactorng_temp_sample']
loggers = {}
loggers[codenames[0]] = ValueLogger(ng_measurement, comp_val = 0.4, comp_type = 'lin')
loggers[codenames[0]].start()

socket = DateDataPullSocket(unichr(0x03BC) + '-reactor NG temperature', codenames, timeouts=[1.0])
socket.start()

livesocket = LiveSocket(unichr(0x03BC) + '-reactors temperatures', codenames, 2)
livesocket.start()

db_logger = ContinuousLogger(table='dateplots_microreactorNG',
                             username=credentials.user,
                             password=credentials.passwd,
                             measurement_codenames=codenames)
db_logger.start()

while ng_measurement.isAlive():
    time.sleep(0.25)
    for name in codenames:
        v = loggers[name].read_value()
        socket.set_point_now(name, v)
        livesocket.set_point_now(name, v)
        if loggers[name].read_trigged():
            print v
            db_logger.enqueue_point_now(name, v)
            loggers[name].clear_trigged()
