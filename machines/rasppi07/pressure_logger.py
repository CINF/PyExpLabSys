# pylint: disable=R0904, C0103

import threading
import logging
import time
import math
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from ABE_DeltaSigmaPi import DeltaSigma
from ABE_helpers import ABEHelpers
import credentials

class PressureReader(threading.Thread):
    """ Read Cooling water pressure """
    def __init__(self, adc):
        threading.Thread.__init__(self)
        self.adc = adc
        self.gaugepressure = -1
        self.quit = False

    def value(self):
        """ Return the value of the reader """
        return(self.gaugepressure)

    def run(self):
        while not self.quit:
            time.sleep(1)
            voltage = self.adc.read_voltage(1)
            self.gaugepressure = math.exp(voltage * 63.95) * 1.4966e-11

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

i2c_helper = ABEHelpers()
bus = i2c_helper.get_smbus()
adc_instance = DeltaSigma(bus, 0x68, 0x69, 18)
pressurereader = PressureReader(adc_instance)
pressurereader.daemon = True
pressurereader.start()

codenames = ['mr_iongauge_pressure']

logger = ValueLogger(pressurereader, comp_val = 0.5)
logger.start()

socket = DateDataPullSocket('Microreactor Ion Gauge', codenames, timeouts=[1.0])
socket.start()

live_socket = LiveSocket('Microreactor Ion Gauge', codenames, 2)
live_socket.start()

db_logger = ContinuousLogger(table='dateplots_microreactor',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=codenames)
db_logger.start()

time.sleep(2)

while True:
    time.sleep(0.25)
    p = logger.read_value()
    socket.set_point_now(codenames[0], p)
    live_socket.set_point_now(codenames[0], p)
    if logger.read_trigged():
        print p
        db_logger.enqueue_point_now(codenames[0], p)
        logger.clear_trigged()
