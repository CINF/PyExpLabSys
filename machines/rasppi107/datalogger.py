""" Pressure and temperature logger """
from __future__ import print_function
import threading
import time
import logging
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.xgs600 as xgs600
import PyExpLabSys.drivers.kjlc_pressure_gauge as kjlc
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)


class PressureReader(threading.Thread):
    """ Sniffer pirani reader """
    def __init__(self, gauge):
        threading.Thread.__init__(self)
        self.gauge = gauge
        self.ttl = 20
        self.pressure = None
        self.quit = False

    def value(self):
        """ Read the temperaure """
        self.ttl = self.ttl - 1
        value = self.pressure
        if self.ttl < 0:
            self.quit = True
            value = None
        return value

    def run(self):
        while not self.quit:
            self.ttl = 20
            self.pressure = self.gauge.read_pressure()
            time.sleep(1)

class XgsReader(threading.Thread):
    """ Pressure reader """
    def __init__(self, xgs):
        threading.Thread.__init__(self)
        self.xgs = xgs
        self.qms = None
        self.qms_r = None
        self.buf_r = None
        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel == 0:
                return_val = self.qms
            if channel == 1:
                return_val = self.qms_r
            if channel == 2:
                return_val = self.buf_r
        return return_val

    def run(self):
        while not self.quit:

            time.sleep(0.5)
            press = self.xgs.read_all_pressures()
            try:
                self.ttl = 50
                self.qms = press[0]
                self.qms_r = press[1]
                self.buf_r = press[2]
            except IndexError:
                print("av")

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    xgs_port = '/dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0'
    xgs_instance = xgs600.XGS600Driver(xgs_port)
    print(xgs_instance.read_all_pressures())

    kjlc_port = '/dev/serial/by-id/usb-Prolific_Technology_Inc._'
    kjlc_port += 'USB-Serial_Controller-if00-port0'
    kjlc_instance = kjlc.KJLC300(kjlc_port)

    xgs_pressure = XgsReader(xgs_instance)
    xgs_pressure.start()

    kjlc_pressure = PressureReader(kjlc_instance)
    kjlc_pressure.start()

    time.sleep(2.5)

    codenames = ['sniffer_qms_ion_gauge',
                 'sniffer_qms_roughing',
                 'sniffer_buffer_roughing',
                 'sniffer_buffer_pressure']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(xgs_pressure, comp_val=0.1,
                                        low_comp=1e-8, comp_type='log', channel=0)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(xgs_pressure, comp_val=0.1,
                                        low_comp=1e-3, comp_type='log', channel=1)
    loggers[codenames[1]].start()
    loggers[codenames[2]] = ValueLogger(xgs_pressure, comp_val=0.1,
                                        low_comp=1e-3, comp_type='log', channel=2)
    loggers[codenames[2]].start()

    loggers[codenames[3]] = ValueLogger(kjlc_pressure, comp_val=0.1, comp_type='lin')
    loggers[codenames[3]].start()

    livesocket = LiveSocket('sniffer pressure logger', codenames)
    livesocket.start()

    socket = DateDataPullSocket('sniffer pressure', codenames,
                                timeouts=[1.0]*len(codenames))
    socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_sniffer',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    while xgs_pressure.isAlive():
        time.sleep(0.25)
        for name in codenames:
            value = loggers[name].read_value()
            livesocket.set_point_now(name, value)
            socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(name, value)
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
