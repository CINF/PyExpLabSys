# pylint: disable= R0904, C0103

import logging
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.chiller_reader import ChillerReader
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import LiveSocket
import credentials

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

chiller_port = '/dev/serial/by-id/'
chiller_port += 'usb-1a86_USB2.0-Ser_-if00-port0'
reader = ChillerReader(chiller_port)
reader.start()

codenames = ['thetaprobe_chiller_temperature', 
             'thetaprobe_chiller_flow', 
             'thetaprobe_chiller_temperature_ambient', 
             'thetaprobe_chiller_pressure', 
             'thetaprobe_chiller_temperature_setpoint']
loggers = {}
for i in range(0, len(codenames)):
    loggers[codenames[i]] = ValueLogger(reader, comp_val = 0.1, channel = i)
    loggers[codenames[i]].start()
live_socket = LiveSocket('Thetaprobe chiller', codenames, 2)
live_socket.start()

db_logger = ContinuousLogger(table='dateplots_thetaprobe',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=codenames)
db_logger.start()

time.sleep(5)

while reader.isAlive():
    time.sleep(0.25)
    for name in codenames:
        v = loggers[name].read_value()
        live_socket.set_point_now(name, v)
        if loggers[name].read_trigged():
            print v
            db_logger.enqueue_point_now(name, v)
            loggers[name].clear_trigged()

