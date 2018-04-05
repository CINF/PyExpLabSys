""" Module for logging QCM Values """
from __future__ import print_function
import threading
import logging
import time
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
import PyExpLabSys.drivers.inficon_sqm160 as inficon
import credentials

class QcmReader(threading.Thread):
    """ Read QCM values """
    def __init__(self, qcm_instance):
        threading.Thread.__init__(self)
        self.qcm = qcm_instance
        self.frequency = -1
        self.lifetime = -1
        self.thickness = -1
        self.ttl = 20
        self.quit = False

    def value(self, channel):
        """ Return the value of the reader """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        if channel == 0:
            return_val = self.frequency
        if channel == 1:
            return_val = self.lifetime
        if channel == 2:
            return_val = self.thickness
        return return_val

    def run(self):
        while not self.quit:
            print(self.ttl)
            self.frequency = self.qcm.frequency()
            self.lifetime = self.qcm.crystal_life()
            self.thickness = self.qcm.thickness()
            self.ttl = 20
            time.sleep(2)

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    qcm_port = ('/dev/serial/by-id/' +
                'usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0')
    qcm = inficon.InficonSQM160(qcm_port)
    reader = QcmReader(qcm)
    reader.daemon = True
    reader.start()

    codenames = ['volvo_qcm_frequency',
                 'volvo_qcm_crystal_life',
                 'volvo_qcm_thickness']
    loggers = {}
    loggers[codenames[0]] = ValueLogger(reader, comp_val=0.1, channel=0)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(reader, comp_val=0.01, channel=1)
    loggers[codenames[1]].start()
    loggers[codenames[2]] = ValueLogger(reader, comp_val=0.001, channel=2)
    loggers[codenames[2]].start()
    socket = DateDataPullSocket('Volvo QCM', codenames, port=9000,
                                timeouts=[5.0] * len(codenames))
    socket.start()

    livesocket = LiveSocket('Volvo data logger', codenames)
    livesocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_volvo',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    time.sleep(5)

    while reader.isAlive():
        time.sleep(0.25)
        for name in codenames:
            value = loggers[name].read_value()
            socket.set_point_now(name, value)
            livesocket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(value)
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
