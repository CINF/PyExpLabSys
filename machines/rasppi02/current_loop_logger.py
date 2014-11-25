# pylint: disable=C0301,R0904, C0103

import threading
import logging
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from ABElectronics_ADCPi import ADCPi
import credentials

class PressureReader(threading.Thread):
    """ Read Cooling water pressure """
    def __init__(self, adc):
        threading.Thread.__init__(self)
        self.adc = adc
        self.waterpressure = -1
        self.quit = False

    def value(self):
        """ Return the value of the reader """
        return(self.waterpressure)

    def run(self):
        while not self.quit:
            time.sleep(1)
            current = (self.adc.readVoltage(1) / 148) * 1000
            self.waterpressure = (current - 4) * (150 / 16) * 0.068947

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

adc_instance = ADCPi(0x68, 0x69, 18)
pressurereader = PressureReader(adc_instance)
pressurereader.daemon = True
pressurereader.start()

logger = ValueLogger(pressurereader, comp_val = 0.5)
logger.start()

socket = DateDataPullSocket('hall_waterpressure',
                            ['hall_coolingwater_pressure'], timeouts=[1.0])
socket.start()

live_socket = LiveSocket('hall_waterpressure', ['hall_coolingwater_pressure'], 2)
live_socket.start()

db_logger = ContinuousLogger(table='dateplots_hall',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=['hall_coolingwater_pressure'])
db_logger.start()

time.sleep(2)

while True:
    time.sleep(0.25)
    p = logger.read_value()
    socket.set_point_now('hall_coolingwater_pressure', p)
    live_socket.set_point_now('hall_coolingwater_pressure', p)
    if logger.read_trigged():
        print p
        db_logger.enqueue_point_now('hall_coolingwater_pressure', p)
        logger.clear_trigged()

