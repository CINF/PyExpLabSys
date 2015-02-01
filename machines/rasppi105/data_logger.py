# pylint: disable=C0301,R0904, C0103

import threading
import logging
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
import PyExpLabSys.drivers.keithley_2700 as keithley2700
import credentials

class DmmReader(threading.Thread):
    def __init__(self, dmm):
        threading.Thread.__init__(self)
        self.dmm = dmm
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
            #print self.ttl
            self.rtd_resistance = self.dmm.read_voltage()
            self.ttl = 20
            time.sleep(2)
    def stop(self,):
        self.quit = True

#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)

dmm_port = '/dev/serial/by-id/usb-9710_7840-if00-port0'
dmm = keithley2700.Keithley2700('serial', device=dmm_port)
reader = DmmReader(dmm)
reader.daemon = True
reader.start()

codenames = ['omicron_rtd_resistance',]
loggers = {}
for i in range(0, len(codenames)):
    loggers[codenames[i]] = ValueLogger(reader, maximumtime=60, comp_type = 'lin', comp_val = 0.1, channel = i)
    loggers[codenames[i]].daemon = True
    loggers[codenames[i]].start()

socket = DateDataPullSocket('omicron_rtd_resistance',
                            codenames, port=9001, timeouts=[5.0] * len(codenames))
socket.daemon = True
socket.start()

#db_logger = ContinuousLogger(table='dateplots_omicron',
#                                 username=credentials.user,
#                                 password=credentials.passwd,
#                                 measurement_codenames=codenames)
#db_logger.daemon = True
#db_logger.start()

time.sleep(5)

run = True
while run:
    time.sleep(0.25)
    try:
        for name in codenames:
            v = loggers[name].read_value()
            socket.set_point_now(name, v)
            if loggers[name].read_trigged():
                print v
                #db_logger.enqueue_point_now(name, v)
                loggers[name].clear_trigged()
                print("resistance: {}, time: {}".format(v, time.time()))
    except (KeyboardInterrupt, SystemExit):
        print('raising error')
        run = False
        raise
    except:
        print('stoppiung everything')
        run = False
        reader.stop()
        socket.stop()
        for value, key in loggers.iteritems():
            value.stop()
        print('All is stopped')


