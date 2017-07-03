""" Pressure logger for sample storage """
from __future__ import print_function
import threading
import logging
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from  ABE_ADCPi import ADCPi
from ABE_helpers import ABEHelpers
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class PressureReader(threading.Thread):
    """ Read Cooling water pressure """
    def __init__(self, adc):
        threading.Thread.__init__(self)
        self.adc = adc
        self.pressure = 0
        self.quit = False

    def value(self):
        """ Return the value of the reader """
        return self.pressure

    def run(self):
        time.sleep(0.2)
        while not self.quit:
            voltage = self.adc.read_voltage(1) * 8 / 5
            pressure = 10**(voltage - 5)
            self.pressure = pressure

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

    codenames = ['chemlab312_sample_storage_pressure']
    loggers = {}
    for i in range(0, 1):
        loggers[codenames[i]] = ValueLogger(pressurereader, comp_val=0.05, comp_type='log')
        loggers[codenames[i]].start()
    socket = DateDataPullSocket('chemlab312_sample_storage',
                                codenames, timeouts=[2.0])
    socket.start()

    live_socket = LiveSocket('chemlab312_sample_storage', codenames)
    live_socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_chemlab312',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    time.sleep(5)

    while True:
        time.sleep(0.5)
        for name in codenames:
            value = loggers[name].read_value()
            socket.set_point_now(name, value)
            live_socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(value)
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()

