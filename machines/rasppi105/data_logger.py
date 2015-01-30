# pylint: disable=C0301,R0904, C0103

import threading
import logging
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
import PyExpLabSys.drivers.keithley2700 as keithley2700
import credentials

class DmmReader(threading.Thread):
    def __init__(self, dmm):
        threading.Thread.__init__(self)
        self.qcm = qcm_instance
        self.rtd_resistance = -1
        #self.rtd_temperature = -1
        self.ttl = 20
        self.quit = False

    def value(self, channel):
        """ Return the value of the reader """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        if channel == 0:
            return_val = self.rtd_resistance
        #if channel == 1:
        #    return_val = self.rtd_temperature
        return return_val

    def run(self):
        while not self.quit:
            print self.ttl
            self.rtd_resistance = self.dmm.read_resistance()
            self.ttl = 20
            time.sleep(2)


logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

dmm_port = '/dev/serial/by-id/usb-9710_7840-if00-port0'
dmm = keithley2700.Keithley2700(dmm_port)
reader = DmmReader(dmm)
reader.daemon = True
reader.start()

codenames = ['omicron_rtd_resistance',]
loggers = {}
for i in range(0, len(codenames)):
    loggers[codenames[i]] = ValueLogger(reader, comp_val = 0.25, channel = i)
    loggers[codenames[i]].start()

socket = DateDataPullSocket('omicron_rtd_resistance',
                            codenames, port=9001, timeouts=[5.0] * len(codenames))
socket.start()

db_logger = ContinuousLogger(table='dateplots_omicron',
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
