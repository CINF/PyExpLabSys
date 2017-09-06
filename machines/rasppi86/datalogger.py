""" Pressure and temperature logger """
from __future__ import print_function
import threading
import time
import logging
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.omegabus as omegabus
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class Reader(threading.Thread):
    """ Pressure reader """
    def __init__(self, omegabus_instance):
        threading.Thread.__init__(self)
        self.omegabus = omegabus_instance
        self.pressure = None
        self.quit = False
        self.ttl = 20

    def value(self):
        """ Read temperature and  pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            return_val = self.pressure
        return return_val

    def run(self):
        while not self.quit:
            self.ttl = 50
            avg_length = 3
            raw_sum = 0
            for _ in range(0, avg_length):
                raw = self.omegabus.read_value(1)
                raw_sum += raw
            raw_avg = raw_sum / (1.0 * avg_length)
            self.pressure = 2068.43 * (raw_avg - 4) / 16.0 # 4-20mA = 0 - 30psi
            #print(self.pressure)

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    port = 'usb-FTDI_USB-RS232_Cable_FTWZKOU0-if00-port0'
    omega = omegabus.OmegaBus(device='/dev/serial/by-id/' + port, model='D5251', baud=300)

    reader = Reader(omega)
    reader.start()

    time.sleep(2.5)

    codenames = ['propene_ox_setup_abs_pressure']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(reader, comp_val=5, maximumtime=300,
                                        comp_type='lin')
    loggers[codenames[0]].start()


    livesocket = LiveSocket('propene_ox Logger', codenames)
    livesocket.start()

    socket = DateDataPullSocket('propene_ox logger', codenames,
                                timeouts=[3.0] * len(loggers))
    socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_propene_ox',
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
