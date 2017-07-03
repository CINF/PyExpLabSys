""" Pressure and temperature logger """
from __future__ import print_function
import threading
import time
import logging
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.omegabus as omegabus
import PyExpLabSys.drivers.omega_cni as omega_CNi32
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class OldTempReader(threading.Thread):
    """ Temperature reader """
    def __init__(self, omega):
        threading.Thread.__init__(self)
        self.omegabus = omega
        self.ttl = 20
        self.temperature = None
        self.quit = False

    def value(self):
        """ Read the temperaure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        return self.temperature

    def run(self):
        while not self.quit:
            self.ttl = 20
            time.sleep(1)
            self.temperature = self.omegabus.read_value(2)


class NGTempReader(threading.Thread):
    """ Temperature reader """
    def __init__(self, omega):
        threading.Thread.__init__(self)
        self.omega = omega
        self.ttl = 20
        self.temperature = None
        self.quit = False

    def value(self):
        """ Read the temperaure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        return self.temperature

    def run(self):
        while not self.quit:
            self.ttl = 20
            time.sleep(1)
            self.temperature = self.omega.read_temperature()

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    port = 'usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
    ng_temp = omega_CNi32.ISeries('/dev/serial/by-id/' + port, 9600)

    port = 'usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'
    old_temp = omegabus.OmegaBus(device='/dev/serial/by-id/' + port, model='D5321', baud=9600)

    ng_measurement = NGTempReader(ng_temp)
    ng_measurement.start()

    old_measurement = OldTempReader(old_temp)
    old_measurement.start()

    time.sleep(2.5)

    codenames = ['microreactorng_temp_sample', 'mr_sample_tc_temperature']
    loggers = {}
    loggers[codenames[0]] = ValueLogger(ng_measurement, comp_val=0.4, comp_type='lin')
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(old_measurement, comp_val=1.0, comp_type='lin')
    loggers[codenames[1]].start()

    try:
        micro = chr(0x03BC) # Python 3
    except ValueError:
        micro = unichr(0x03BC) # Python 2

    socket = DateDataPullSocket(micro + '-reactor NG temperature',
                                codenames, timeouts=5)
    socket.start()

    livesocket = LiveSocket(micro + '-reactors temperatures', codenames)
    livesocket.start()

    db_logger = {}
    db_logger[codenames[0]] = ContinuousDataSaver(
        continuous_data_table='dateplots_microreactorNG',
        username=credentials.user_new,
        password=credentials.passwd_new,
        measurement_codenames=codenames
    )

    db_logger[codenames[1]] = ContinuousDataSaver(
        continuous_data_table='dateplots_microreactor',
        username=credentials.user_old,
        password=credentials.passwd_old,
        measurement_codenames=codenames
    )

    db_logger[codenames[0]].start()
    db_logger[codenames[1]].start()

    while ng_measurement.isAlive():
        time.sleep(0.25)
        for name in codenames:
            value = loggers[name].read_value()
            socket.set_point_now(name, value)
            livesocket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(value)
                db_logger[name].save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
