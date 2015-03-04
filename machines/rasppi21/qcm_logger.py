# pylint: disable=C0301,R0904, C0103

import threading
import logging
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
import PyExpLabSys.drivers.inficon_sqm160 as inficon
import credentials

class QcmReader(threading.Thread):
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
            print self.ttl
            self.frequency = self.qcm.frequency()
            self.lifetime = self.qcm.crystal_life()
            self.thickness =  self.qcm.thickness()
            self.ttl = 20
            time.sleep(2)


logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

qcm_port = '/dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0'
qcm = inficon.InficonSQM160(qcm_port)
reader = QcmReader(qcm)
reader.daemon = True
reader.start()

codenames = ['sputterchamber_qcm_frequency', 
             'sputterchamber_qcm_qrystal_life', 
             'sputterchamber_qcm_thickness']
loggers = {}
for i in range(0, len(codenames)):
    loggers[codenames[i]] = ValueLogger(reader, comp_val = 0.25, channel = i)
    loggers[codenames[i]].start()
socket = DateDataPullSocket('Sputterchamber QCM',
                            codenames, port=9001, timeouts=[5.0] * len(codenames))
socket.start()

db_logger = ContinuousLogger(table='dateplots_sputterchamber',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=codenames)
db_logger.start()

time.sleep(5)

while reader.isAlive():
    time.sleep(0.25)
    for name in codenames:
        v = loggers[name].read_value()
        socket.set_point_now(name, v)
        if loggers[name].read_trigged():
            print v
            db_logger.enqueue_point_now(name, v)
            loggers[name].clear_trigged()

