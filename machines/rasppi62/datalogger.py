""" Pressure and temperature logger """
from __future__ import print_function
import threading
import time
import logging
import numpy as np
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.dataq_comm as dataq
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class Reader(threading.Thread):
    """ Pressure reader """
    def __init__(self, dataq_instance):
        threading.Thread.__init__(self)
        self.dataq = dataq_instance
        self.pressure = {}
        self.pressure['main_pirani'] = None
        self.pressure['main_baratron'] = None
        self.pressure['main_ion_gauge'] = None
        self.pressure['load_lock'] = None
        self.pressure['roughing_ll'] = None
        self.pressure['roughing_main'] = None
        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read values """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
            print('TTL failed')
            exit()
        else:
            if channel == 1:
                return_val = self.pressure['main_pirani']
            if channel == 2:
                return_val = self.pressure['main_baratron']
            if channel == 3:
                return_val = self.pressure['main_ion_gauge']
            if channel == 4:
                return_val = self.pressure['load_lock']
            if channel == 5:
                return_val = self.pressure['roughing_ll']
            if channel == 6:
                return_val = self.pressure['roughing_main']
        return return_val


    def run(self):
        while not self.quit:
            self.ttl = 150
            values = np.zeros(6)
            average_length = 100
            for _ in range(0, average_length):
                measurements = self.dataq.read_measurements()
                values[0] += measurements[1]
                values[1] += measurements[2]
                values[2] += measurements[3]
                values[3] += measurements[4]
                values[4] += measurements[5]
                values[5] += measurements[6]
            values = values / average_length
            self.pressure['main_pirani'] = 10**(values[0]-2)
            self.pressure['main_baratron'] = values[1] / 100
            self.pressure['main_ion_gauge'] = 10**(-1*values[2]-12)
            self.pressure['load_lock'] = 0
            self.pressure['roughing_ll'] = 1.11985865e-5*(3.11878295**values[4])
            self.pressure['roughing_main'] = 1.11985865e-5*(3.11878295**values[5])
            time.sleep(0.5)

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    dataq_instance = dataq.DataQ('/dev/serial/by-id/usb-0683_1490-if00')
    for i in range(1, 7):
        dataq_instance.add_channel(i)
    dataq_instance.start_measurement()
    reader = Reader(dataq_instance)
    reader.start()

    time.sleep(10)

    codenames = ['sputterchamber_pressure_pirani', 'sputterchamber_baratron_pressure',
                 'sputterchamber_pressure_iongauge', 'sputterchamber_ll_pressure',
                 'sputterchamber_ll_rough_pressure', 'sputterchamber_rough_pressure']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(reader, comp_val=0.02, low_comp=1e-4, maximumtime=600,
                                        comp_type='log', channel=1)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(reader, comp_val=0.001, low_comp=1e-4, maximumtime=600,
                                        comp_type='lin', channel=2)
    loggers[codenames[1]].start()
    loggers[codenames[2]] = ValueLogger(reader, comp_val=0.02, maximumtime=600, low_comp=1e-9,
                                        comp_type='log', channel=3)
    loggers[codenames[2]].start()
    loggers[codenames[3]] = ValueLogger(reader, comp_val=1, low_comp=1e-5, maximumtime=6000,
                                        comp_type='log', channel=4)
    loggers[codenames[3]].start()
    loggers[codenames[4]] = ValueLogger(reader, comp_val=0.15, low_comp=1e-3, maximumtime=600,
                                        comp_type='log', channel=5)
    loggers[codenames[4]].start()
    loggers[codenames[5]] = ValueLogger(reader, comp_val=0.25, low_comp=1e-1, maximumtime=600,
                                        comp_type='log', channel=6)
    loggers[codenames[5]].start()


    livesocket = LiveSocket('Sputterchamber pressures', codenames)
    livesocket.start()

    socket = DateDataPullSocket('Sputterchamber pressures', codenames,
                                timeouts=[2.0] * len(loggers))
    socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_sputterchamber',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    while reader.isAlive():
        time.sleep(1)
        for name in codenames:
            value = loggers[name].read_value()
            livesocket.set_point_now(name, value)
            socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(name + ': ' + str(value))
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
