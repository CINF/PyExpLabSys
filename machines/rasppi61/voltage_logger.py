# pylint: disable=C0301,R0904, C0103
import os
import threading
import logging
import time
import subprocess
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from ABE_helpers import ABEHelpers
#from ABE_ADCPi import ADCPi
from ABE_DeltaSigmaPi import DeltaSigma
import credentials

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
                temp_hot += adc_instance.read_voltage(1)
                temp_cold += adc_instance.read_voltage(2)
            self.hot = (temp_hot/4 - 0.4) / 0.0195
            self.cold = (temp_cold/4 - 0.4) / 0.0195 - 3.5

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
    loggers[codenames[i]] = ValueLogger(tempreader, comp_val = 0.5, channel = i)
    loggers[codenames[i]].start()
socket = DateDataPullSocket('hall_cooling_water_temp',
                            codenames, timeouts=[2.0, 2.0])
socket.start()

live_socket = LiveSocket('hall_waterpressure', codenames)
live_socket.start()

db_logger = ContinuousLogger(table='dateplots_hall',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=codenames)
db_logger.start()

time.sleep(5)

while True:
    time.sleep(0.25)
    for name in codenames:
        v = loggers[name].read_value()
        socket.set_point_now(name, v)
        live_socket.set_point_now(name, v)
        if loggers[name].read_trigged():
            print v
            db_logger.enqueue_point_now(name, v)
            loggers[name].clear_trigged()

