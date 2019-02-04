# -*- coding: utf-8 -*-
""" Logs fume hood wind speed

Be aware that absolute calibration migh not be amasingly
good due to differences between each sensor and because of
temperature dependence of the measurement. For this reason
both the analog value as well as the calculated wind speed
is logged, to allow the possibility of a later correction
if a better calibration is performed.

The fitting function was dertmined in a DTU student project:
'Test and calibration of simple hot-wire anemometer for better
lab safety' in January 2017
by Kristine Børsting (s153299) and Bianca Laura Hansen (s163993)
"""
from __future__ import print_function
import threading
import time
import sys
import math
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.supported_versions import python2_and_3
from ABE_ADCPi import ADCPi
from ABE_helpers import ABEHelpers
python2_and_3(__file__)
try:
    sys.path.append('/home/pi/PyExpLabSys/machines/' + sys.argv[1])
except IndexError:
    print('You need to give the name of the raspberry pi as an argument')
    print('This will ensure that the correct settings file will be used')
    exit()
import credentials # pylint: disable=import-error, wrong-import-position
import settings # pylint: disable=import-error, wrong-import-position

class WindReader(threading.Thread):
    """ Read Cooling water pressure """
    def __init__(self, adc):
        threading.Thread.__init__(self)
        self.adc = adc
        self.average_length = 10
        self.windspeeds = {}
        for channel in settings.channels.keys():
            self.windspeeds[channel] = -1
            self.windspeeds[channel+'_raw'] = -1
            self.quit = False

    def value(self, channel):
        """ Return the value of the reader """
        value = self.windspeeds[channel]
        return value

    def run(self):
        time.sleep(0.1)
        while not self.quit:
            for channel in settings.channels.keys():
                voltage = 0
                for _ in range(0, self.average_length):
                    voltage += self.adc.read_voltage(int(channel))
                raw = voltage / self.average_length
                self.windspeeds[channel + '_raw'] = raw
                coeff_a = 0.591
                coeff_b = 1.78
                coeff_c = 2.25
                try:
                    self.windspeeds[channel] = (-1 * (1/coeff_c) *
                                                math.log(1- (raw - coeff_b) / coeff_a))
                except ValueError:
                    pass

def main():
    """ Main function """
    i2c_helper = ABEHelpers()
    bus = i2c_helper.get_smbus()
    adc_instance = ADCPi(bus, 0x68, 0x69, 18)

    windreader = WindReader(adc_instance)
    windreader.daemon = True
    windreader.start()

    loggers = {}
    for channel, codename in settings.channels.items():
        loggers[codename + '_raw'] = ValueLogger(windreader, comp_val=1.05,
                                                 channel=channel + '_raw', maximumtime=30)
        loggers[codename + '_raw'].start()
        loggers[codename] = ValueLogger(windreader, comp_val=1.005,
                                        channel=channel, maximumtime=30)
        loggers[codename].start()

    codenames = []
    for name in settings.channels.values():
        codenames.append(name)
        codenames.append(name + '_raw')

    socket = DateDataPullSocket('Fumehood Wind Speed', codenames, timeouts=2.0)
    socket.start()

    live_socket = LiveSocket('Fumehood Wind Speed', codenames)
    live_socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table=settings.dateplot_table,
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    time.sleep(10)

    while windreader.is_alive():
        time.sleep(0.25)
        for name in codenames:
            value = loggers[name].read_value()
            socket.set_point_now(name, value)
            live_socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(name + ': ' + str(value))
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
