""" Logger of cooling water temperature """
from __future__ import print_function
import os
import threading
import logging
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.supported_versions import python2_and_3
from ABE_helpers import ABEHelpers
from ABE_DeltaSigmaPi import DeltaSigma
import credentials
python2_and_3(__file__)

class TemperatureReader(threading.Thread):
    """ Read Cooling water pressure """
    def __init__(self, adc):
        threading.Thread.__init__(self)
        self.adc = adc
        self.hot = -1
        self.cold = -1
        self.quit = False

    def value(self, channel):
        """ Return the value of the reader """
        if channel == 0:
            value = self.hot
        if channel == 1:
            value = self.cold
        return value

    def run(self):
        time.sleep(0.1)
        while not self.quit:
            #temp_str = subprocess.check_output(['cat',
            #                                    '/sys/class/thermal/thermal_zone0/temp'])
            temp_str = 0.0
            temp = float(temp_str) / 1000
            os.environ['cpu_temperature'] = str(temp)

            temp_hot = 0
            temp_cold = 0
            for _ in range(0, 4):
                #temp_hot += adc_instance.read_voltage(1)
                #temp_cold += adc_instance.read_voltage(2)
                temp_hot += self.adc.read_voltage(1)
                temp_cold += self.adc.read_voltage(2)

            self.hot = (temp_hot/4 - 0.4) / 0.0195
            self.cold = (temp_cold/4 - 0.4) / 0.0195 - 3.5


def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    i2c_helper = ABEHelpers()
    bus = i2c_helper.get_smbus()
    adc_instance = DeltaSigma(bus, 0x68, 0x69, 18)

    tempreader = TemperatureReader(adc_instance)
    tempreader.daemon = True
    tempreader.start()

    codenames = ['cooling_water_hot', 'cooling_water_cold']
    loggers = {}
    for i in range(0, 2):
        loggers[codenames[i]] = ValueLogger(tempreader, comp_val=0.25, channel=i)
        loggers[codenames[i]].start()
    socket = DateDataPullSocket('hall_cooling_water_temp',
                                codenames, timeouts=2.0)
    socket.start()

    live_socket = LiveSocket('hall_waterpressure', codenames)
    live_socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_hall',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    time.sleep(5)

    while tempreader.is_alive():
        time.sleep(0.25)
        for name in codenames:
            value = loggers[name].read_value()
            socket.set_point_now(name, value)
            live_socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(value)
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    while True:
        try:
            main()
        except KeyboardInterrupt:
            print("Quitting")
            break
        except OSError as exception:  # Network problem
            print("Got '{}'. Wait 5 min and restart".format(exception))
            time.sleep(300)
