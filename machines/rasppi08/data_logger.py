# pylint: disable=C0301,R0904, C0103
import threading
import logging
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
import PyExpLabSys.drivers.omegabus as omegabus
import PyExpLabSys.drivers.NGC2D as NGC2D
import credentials

class Reader(threading.Thread):
    def __init__(self, iongauge, omega):
        threading.Thread.__init__(self)
        self.iongauge = iongauge
        self.oemga = omega
        self.temperature = {0: -1, }
        self.pressure = -1
        self.ttl = 20
        self.quit = False
    def value(self, channel):
        """ Return the value of the reader """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            if channel == 0:
                return_value = self.pressure
            if channel == 1:
                return_val = self.temperature[0]
            if channel == 2:
                return_val = self.temperature[1]
        return return_val
    def run(self):
        while not self.quit:
            value = self.iongauge.ReadPressure()
            if isinstance(value, float):
                self.pressure = value
            for i in range(2):
                value = self.omega.ReadValue(i)
                if isinstance(value, float):
                    self.temperature[i] = value
            self.ttl = 20
            time.sleep(2)
    def stop(self,):
        self.quit = True


ngc2d_port = '/dev/serial/by-id/usb-9710_7840-if00-port0'
omega_port = 'usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
iongauge = NGC2d.NGC2d(device=ngc2d_port)
omega = omegabus.OmegaBus(device=omega_port)
reader = Reader(iongauge, omega)
reader.daemon = True
reader.start()

codenames = ['omicron_nanobeam_pressure', 'omicron_nanobeam_temperature']
loggers = {}
for i in range(0, len(codenames)):
    loggers[codenames[i]] = ValueLogger(reader, maximumtime=60, comp_type = 'lin', comp_val = 0.1, channel = i)
    loggers[codenames[i]].daemon = True
    loggers[codenames[i]].start()
socket = DateDataPullSocket('omicron_nanobeam',
                            codenames, port=9000, timeouts=[5.0] * len(codenames))
socket.daemon = True
socket.start()

#db_logger = ContinuousLogger(table='dateplots_omicron',
#                             username=credentials.user,
#                             password=credentials.passwd,
#                             measurement_codenames=codenames)
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
