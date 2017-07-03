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
    def __init__(self, dataq):
        threading.Thread.__init__(self)
        self.dataq = dataq
        self.pressure = {}
        self.pressure['medium'] = None
        self.pressure['high'] = None
        self.pressure['bpr'] = None
        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read values """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel == 1:
                return_val = self.pressure['medium']
            if channel == 2:
                return_val = self.pressure['high']
            if channel == 3:
                return_val = self.pressure['bpr']
        return return_val

    def run(self):
        while not self.quit:
            pressures = []
            self.ttl = 50
            values = np.zeros(3)
            average_length = 10
            for i in range(0, average_length):
                measurements = self.dataq.read_measurements()
                values[0] += measurements[1]
                values[1] += measurements[2]
                values[2] += measurements[3]
            values = values / average_length
            self.pressure['medium'] = (1.0/5) * (values[0] - 0.1) * 7910.55729 - 15.8
            self.pressure['high'] = (1.0/5) * (values[1] - 0.1) * 206842.719
            self.pressure['bpr'] = (-1.0/10) * values[2] * 2068.42719
            time.sleep(0.2)

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    dataq_instance = dataq.DataQ('/dev/serial/by-id/usb-0683_1550-if00')
    dataq_instance.add_channel(1)
    dataq_instance.add_channel(2)
    dataq_instance.add_channel(3)
    dataq_instance.start_measurement()
    reader = Reader(dataq_instance)
    reader.start()

    time.sleep(2.5)

    codenames = ['vhp_medium_pressure', 'vhp_high_pressure', 'vhp_pressure_bpr_backside']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(reader, comp_val=20, maximumtime=600,
                                        comp_type='lin', channel=1)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(reader, comp_val=500, maximumtime=600,
                                        comp_type='lin', channel=2)
    loggers[codenames[1]].start()
    loggers[codenames[2]] = ValueLogger(reader, comp_val=20, maximumtime=600,
                                        comp_type='lin', channel=3)
    loggers[codenames[2]].start()

    livesocket = LiveSocket('VHP Gas system pressure', codenames)
    livesocket.start()

    socket = DateDataPullSocket('VHP Gas system pressure', codenames,
                                timeouts=[2.0] * len(loggers))
    socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_vhp_setup',
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
