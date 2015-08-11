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
            value = self.pressure['old']
        if channel == 1:
            value = self.pressure['ng']
        if self.ttl < 0:
            self.quit = True
            value = None
        return(value)

    def run(self):
        while not self.quit:
            self.ttl = 20
            for key in ['old', 'ng']:
                self.pressure[key] = self.gauges[key].read_pressure()
            time.sleep(0.1)

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

ports = ['/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTWRZWVS-if00-port0',
         '/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTWXB4EW-if00-port0']

mks_list = {}
for i in range(0, 2):
    _mks = mks_925_pirani.mks_comm(ports[i])
    _name = _mks.read_serial()
    #_name = _name.strip()
    if _name == '1107638964':
        mks_list['ng'] = mks_925_pirani.mks_comm(ports[i])
        mks_list['ng'].change_unit('MBAR')
        print('Pirani, ng buffer:' + ports[i] + ', serial:' + _name)
    elif _name == '1027033634':
        mks_list['old'] = mks_925_pirani.mks_comm(ports[i])
        mks_list['old'].change_unit('MBAR')
        print('Pirani, old buffer:'+ ports[i] + ', serial:' + _name)
    else:
        print('Pirani, Unknown:'+ ports[i] + ', serial:' + _name)
        print(_mks.read_serial())

if len(mks_list) == 2:
    measurement = Reader(mks_list)
    measurement.start()
    
    time.sleep(2.5)
    
    codenames = ['mr_buffer_pressure', 'microreactorng_pressure_buffer']

    loggers = {}
    for i in range(len(codenames)):
        loggers[codenames[i]] = ValueLogger(measurement, comp_val = 0.1,
                                            low_comp = 1e-4, comp_type = 'log',
                                            channel=i)
        loggers[codenames[i]].start()

    socket = DateDataPullSocket(unichr(0x03BC) + '-reactor NG temperature', 
                                codenames, timeouts=[1.0,1.0])
    socket.start()
    
    livesocket = LiveSocket(unichr(0x03BC) + '-reactors pressures',
                            codenames, 0.2)
    livesocket.start()

    db_logger = {} 
    db_logger[codenames[0]] = ContinuousLogger(table='dateplots_microreactor',
                                 username=credentials.user_old,
                                 password=credentials.passwd_old,
                                 measurement_codenames=codenames)

    db_logger[codenames[1]] = ContinuousLogger(table='dateplots_microreactorNG',
                                 username=credentials.user_new,
                                 password=credentials.passwd_new,
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
            print "Codename: {}".format(name)
            print "Value: {}".format(v)
            print '---'
            db_logger[name].enqueue_point_now(name, v)
            loggers[name].clear_trigged()

