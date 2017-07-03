""" Logger of cooling water temperature """
from __future__ import print_function
import threading
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.supported_versions import python2_and_3
from ABE_DeltaSigmaPi import DeltaSigma
from ABE_helpers import ABEHelpers
import credentials
python2_and_3(__file__)

class WindReader(threading.Thread):
    """ Read Cooling water pressure """
    def __init__(self, adc):
        threading.Thread.__init__(self)
        self.adc = adc
        self.average_length = 10
        self.out_voltage = None
        self.raw_voltage = None
        self.quit = False

    def value(self, channel):
        """ Return the value of the reader """
        if channel == 0:
            value = self.out_voltage
        if channel == 1:
            value = self.raw_voltage
        return value

    def run(self):
        time.sleep(0.1)
        while not self.quit:
            out_voltage = 0
            raw_voltage = 0
            for _ in range(0, self.average_length):
                out_voltage += self.adc.read_voltage(5)
                raw_voltage += self.adc.read_voltage(2)
            self.out_voltage = out_voltage / self.average_length
            self.raw_voltage = raw_voltage / self.average_length


def main():
    """ Main function """
    i2c_helper = ABEHelpers()
    bus = i2c_helper.get_smbus()
    adc_instance = DeltaSigma(bus, 0x68, 0x69, 18)

    windreader = WindReader(adc_instance)
    windreader.daemon = True
    windreader.start()

    codenames = ['b312_fumehood_01_windspeed_out', 'b312_fumehood_01_windspeed_raw']
    loggers = {}
    for i in range(0, 2):
        loggers[codenames[i]] = ValueLogger(windreader, comp_val=0.01, channel=i)
        loggers[codenames[i]].start()
    socket = DateDataPullSocket('Fumehood Wind Speed', codenames, timeouts=2.0)
    socket.start()

    live_socket = LiveSocket('Fumehood Wind Speed', codenames)
    live_socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_dummy',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    time.sleep(5)

    while windreader.is_alive():
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
    main()
