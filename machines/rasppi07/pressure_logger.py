""" Ion Gauge Logger for Microreactor """
from __future__ import print_function
import threading
import logging
import time
import math
from ABE_DeltaSigmaPi import DeltaSigma
from ABE_helpers import ABEHelpers
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class PressureReader(threading.Thread):
    """ Read Cooling water pressure """
    def __init__(self, adc):
        threading.Thread.__init__(self)
        self.adc = adc
        self.gaugepressure = -1
        self.quit = False

    def value(self):
        """ Return the value of the reader """
        return self.gaugepressure

    def run(self):
        while not self.quit:
            time.sleep(1)
            voltage = self.adc.read_voltage(1)
            self.gaugepressure = math.exp(voltage * 63.95) * 1.4966e-11

def main():
    """ Main function """

    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    i2c_helper = ABEHelpers()
    bus = i2c_helper.get_smbus()
    adc_instance = DeltaSigma(bus, 0x68, 0x69, 18)
    pressurereader = PressureReader(adc_instance)
    pressurereader.daemon = True
    pressurereader.start()

    codenames = ['mr_iongauge_pressure']

    logger = ValueLogger(pressurereader, comp_val=0.5)
    logger.start()

    socket = DateDataPullSocket('Microreactor Ion Gauge', codenames, timeouts=[1.0])
    socket.start()

    live_socket = LiveSocket('Microreactor Ion Gauge', codenames)
    live_socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_microreactor',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    time.sleep(2)

    while True:
        time.sleep(0.25)
        value = logger.read_value()
        socket.set_point_now(codenames[0], value)
        live_socket.set_point_now(codenames[0], value)
        if logger.read_trigged():
            print(value)
            db_logger.save_point_now(codenames[0], value)
            logger.clear_trigged()

if __name__ == '__main__':
    main()
