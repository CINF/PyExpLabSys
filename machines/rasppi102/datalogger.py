""" Pressure and temperature logger """
# pylint: disable=R0904, C0103

import threading
import time
import logging
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.mks_925_pirani as mks_925_pirani
import credentials

class Reader(threading.Thread):
    """ Temperature reader """
    def __init__(self, gauges):
        threading.Thread.__init__(self)
        self.gauges = gauges
        self.ttl = 20
        self.pressure = {}
        self.quit = False

    def value(self, channel):
        """ Read the temperaure """
        self.ttl = self.ttl - 1
        if channel == 0:
            value = self.pressure['ng']
        if channel == 1:
            value = self.pressure['old']
        if self.ttl < 0:
            self.quit = True
            value = None
        return(value)

    def run(self):
        while not self.quit:
            self.ttl = 20
            self.pressure['ng'] = self.gauges['ng'].read_pressure()
            self.pressure['old'] = self.gauges['old'].read_pressure()
            time.sleep(1)

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

name = {}
mks = mks_925_pirani.mks_comm('/dev/ttyUSB0')
name[0] = mks.read_serial()
name[0] = name[0].strip()
print name[0]

mks = mks_925_pirani.mks_comm('/dev/ttyUSB1')
name[1] = mks.read_serial()
name[1] = name[1].strip()
print name[1]

mks_list = {}
for i in range(0, 2):
    if name[i] == '1107638964':
        mks_list['old'] = mks_925_pirani.mks_comm('/dev/ttyUSB' + str(i))
        mks_list['old'].change_unit('MBAR')

        print('Pirani, buffer:/dev/ttyUSB' + str(i) + ', serial:' + name[i])

    if name[i] == '1027033634':
        mks_list['ng'] = mks_925_pirani.mks_comm('/dev/ttyUSB' + str(i))
        mks_list['ng'].change_unit('MBAR')
        print('Pirani, old buffer:/dev/ttyUSB' + str(i) + ', serial:' + name[i])

measurement = Reader(mks_list)
measurement.start()

time.sleep(2.5)

codenames = ['microreactorng_pressure_buffer', 'mr_buffer_pressure']
loggers = {}
loggers[codenames[0]] = ValueLogger(measurement, comp_val = 0.1,
                                    low_comp = 1e-4, comp_type = 'log',
                                    channel=0)
loggers[codenames[0]].start()
loggers[codenames[1]] = ValueLogger(measurement, comp_val = 0.1,
                                    low_comp = 1e-4, comp_type = 'log',
                                    channel=1)
loggers[codenames[1]].start()

socket = DateDataPullSocket(unichr(0x03BC) + '-reactor NG temperature', codenames, timeouts=[1.0, 1.0])
socket.start()

livesocket = LiveSocket(unichr(0x03BC) + '-reactors pressures', codenames, 2)
livesocket.start()

db_logger = {} 
db_logger[codenames[0]] = ContinuousLogger(table='dateplots_microreactorNG',
                                 username=credentials.user_new,
                                 password=credentials.passwd_new,
                                 measurement_codenames=codenames)

db_logger[codenames[1]] = ContinuousLogger(table='dateplots_microreactor',
                                 username=credentials.user_old,
                                 password=credentials.passwd_old,
                                 measurement_codenames=codenames)
db_logger[codenames[0]].start()
db_logger[codenames[1]].start()

while measurement.isAlive():
    time.sleep(0.25)
    for name in codenames:
        v = loggers[name].read_value()
        socket.set_point_now(name, v)
        livesocket.set_point_now(name, v)
        if loggers[name].read_trigged():
            print name
            print v
            print '---'
            db_logger[name].enqueue_point_now(name, v)
            loggers[name].clear_trigged()
