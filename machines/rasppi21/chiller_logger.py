# pylint: disable= R0904, C0103

import threading
import logging
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
import PyExpLabSys.drivers.polyscience_4100 as polyscience_4100
import credentials

class ChillerReader(threading.Thread):
    def __init__(self, chiller_instance):
        threading.Thread.__init__(self)
        self.chiller = chiller_instance
        self.temp = -9999
        self.flow = -9999
        self.temp_amb = -9999
        self.pressure = -9999
        self.temp_setpoint = -9999
        self.status = 'Off'
        self.ttl = 100
        self.quit = False

    def value(self, channel):
        """ Return the value of the reader """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        if channel == 0:
            return_val = self.temp
        if channel == 1:
            return_val = self.flow
        if channel == 2:
            return_val = self.temp_amb
        if channel == 3:
            return_val = self.pressure
        if channel == 4:
            return_val = self.temp_setpoint
        return return_val

    def run(self):
        while not self.quit:
            print self.ttl
            self.temp = self.chiller.read_temperature()
            self.flow = self.chiller.read_flow_rate()
            self.temp_amb = self.chiller.read_ambient_temperature()
            self.pressure = self.chiller.read_pressure()
            self.temp_setpoint = self.chiller.read_setpoint()
            self.status = self.chiller.read_status()
            self.ttl = 100
            time.sleep(1)

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

chiller_port = '/dev/serial/by-id/'
chiller_port += 'usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'

chiller = polyscience_4100.Polyscience_4100(chiller_port)
reader = ChillerReader(chiller)
reader.daemon = True
reader.start()

codenames = ['sputterchamber_chiller_temperature', 
             'sputterchamber_chiller_flow', 
             'sputterchamber_chiller_temperature_ambient', 
             'sputterchamber_chiller_pressure', 
             'sputterchamber_chiller_temperature_setpoint']
loggers = {}
for i in range(0, len(codenames)):
    loggers[codenames[i]] = ValueLogger(reader, comp_val = 0.1, channel = i)
    loggers[codenames[i]].start()
socket = DateDataPullSocket('Sputterchamber chiller',
                            codenames, timeouts=[5.0] * len(codenames))
socket.start()

live_socket = LiveSocket('Sputterchamber chiller', codenames, 2)
live_socket.start()

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
        print 'V: ' + str(v)
        socket.set_point_now(name, v)
        live_socket.set_point_now(name, v)
        if loggers[name].read_trigged():
            print v
            db_logger.enqueue_point_now(name, v)
            loggers[name].clear_trigged()

