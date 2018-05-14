""" Pressure and temperature logger """
from __future__ import print_function
import threading
import time
import logging
import math
import numpy as np
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.stmicroelectronics_l3g4200d as l3g4200d
import PyExpLabSys.drivers.stmicroelectronics_ais328dq as ais328dq
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class Reader(threading.Thread):
    """ Pressure reader """
    def __init__(self, sensor):
        threading.Thread.__init__(self)
        self.sensor = sensor
        self.rms_vibration = None
        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read temperature and  pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel == 0:
                return_val = self.rms_vibration
        return return_val

    def run(self):
        while not self.quit:
            time.sleep(2)
            self.ttl = 50
            avg_length = 1000
            values = np.zeros(avg_length)
            t_start = time.time()
            for i in range(0, avg_length):
                raw = self.sensor.read_values()
                values[i] = math.sqrt(raw[0]**2 + raw[1]**2 + raw[2]**2)
            measurement_time = time.time() - t_start
            print(measurement_time)
            print('Measurement frequency: ' + str(avg_length / measurement_time))
            rms_value = np.sqrt(np.mean(np.square(values))) # pylint: disable=no-member
            self.rms_vibration = rms_value

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    l3g4200d_instance = l3g4200d.L3G4200D()
    l3g4200d_reader = Reader(l3g4200d_instance)
    l3g4200d_reader.start()

    ais328dq_instance = ais328dq.AIS328DQTR()
    ais328dq_reader = Reader(ais328dq_instance)
    ais328dq_reader.start()

    time.sleep(2.5)

    codenames = ['b307_049_vibration_measurement', 'b307_049_vibration_measurement_accl']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(l3g4200d_reader, comp_val=0.02, maximumtime=600,
                                        comp_type='lin', channel=0)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(ais328dq_reader, comp_val=0.01, maximumtime=100,
                                        comp_type='lin', channel=0)
    loggers[codenames[1]].start()

    livesocket = LiveSocket('307 Vibraton logger', codenames)
    livesocket.start()

    socket = DateDataPullSocket('307 vibration logger', codenames,
                                timeouts=[1.0] * len(loggers))
    socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_b307_049',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    while l3g4200d_reader.isAlive():
        time.sleep(10)
        for name in codenames:
            value = loggers[name].read_value()
            print(value)
            livesocket.set_point_now(name, value)
            socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(name + ': ' + str(value))
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
