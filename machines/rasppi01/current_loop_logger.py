""" Argon pressure measuring """
from __future__ import print_function
import threading
import logging
import time
from ABE_helpers import ABEHelpers
from ABE_ADCPi import ADCPi
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class PressureReader(threading.Thread):
    """ Read argon pressure """
    def __init__(self, adc):
        threading.Thread.__init__(self)
        self.adc = adc
        self.waterpressure = -1
        self.quit = False

    def value(self):
        """ Return the value of the reader """
        return self.waterpressure

    def run(self):
        while not self.quit:
            time.sleep(1)
            current = (self.adc.read_voltage(1) / 148) * 1000
            self.waterpressure = (current - 4) * (500 / 16) * 0.068947

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    i2c_helper = ABEHelpers()
    bus = i2c_helper.get_smbus()
    adc_instance = ADCPi(bus, 0x68, 0x69, 18)
    pressurereader = PressureReader(adc_instance)
    pressurereader.daemon = True
    pressurereader.start()

    logger = ValueLogger(pressurereader, comp_val=0.5)
    logger.start()

    socket = DateDataPullSocket('hall_n5_argon_pressure',
                                ['n5_argon_pressure'], timeouts=[1.0])
    socket.start()

    live_socket = LiveSocket('hall_n5_argon_pressure', ['n5_argon_pressure'])
    live_socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_hall',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=['n5_argon_pressure'])
    db_logger.start()

    time.sleep(2)

    while True:
        time.sleep(0.25)
        value = logger.read_value()
        socket.set_point_now('n5_argon_pressure', value)
        live_socket.set_point_now('n5_argon_pressure', value)
        if logger.read_trigged():
            print(value)
            db_logger.save_point_now('n5_argon_pressure', value)
            logger.clear_trigged()

if __name__ == '__main__':
    main()
