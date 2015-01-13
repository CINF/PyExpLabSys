""" Data logger for the mobile gas wall """
# pylint: disable=C0301,R0904, C0103

import threading
import logging
import time
import minimalmodbus
import serial
import PyExpLabSys.drivers.agilent_34410A as dmm
import PyExpLabSys.auxiliary.rtd_calculator as rtd_calculator
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
import credentials


class TcReader(threading.Thread):
    """ Communicates with the Omega ?? """
    def __init__(self, port):
        self.comm = minimalmodbus.Instrument('/dev/serial/by-id/' + port, 1)
        self.comm.serial.baudrate = 9600
        self.comm.serial.parity = serial.PARITY_EVEN
        self.comm.serial.timeout = 0.5
        self.temperature = self.comm.read_register(4096, 1)
        threading.Thread.__init__(self)
        self.quit = False

    def value(self):
        """ Return current value of reader """
        return(self.temperature)

    def run(self):
        while not self.quit:
            time.sleep(0.1)
            self.temperature = self.comm.read_register(4096, 1)

class RtdReader(threading.Thread):
    """ Read resistance of RTD and calculate temperature """
    def __init__(self, address, calib_temp):
        self.rtd_reader = dmm.Agilent34410ADriver(address, port='lan')
        self.rtd_reader.select_measurement_function('FRESISTANCE')
        self.calib_temp = calib_temp
        time.sleep(0.2)
        self.calib_value = self.rtd_reader.read()
        self.rtd_calc = rtd_calculator.RTD_Calculator(calib_temp, self.calib_value)
        threading.Thread.__init__(self)
        self.temperature = None
        self.quit = False

    def value(self):
        """ Return current value of reader """
        return(self.temperature)

    def run(self):
        while not self.quit:
            time.sleep(0.1)
            rtd_value = self.rtd_reader.read()
            self.temperature = self.rtd_calc.find_temperature(rtd_value)

if __name__ == '__main__':
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    ports = {}
    ports[0] = 'usb-FTDI_USB-RS485_Cable_FTWGRMCG-if00-port0'
    ports[1] = 'mobile-gaswall-agilent-34410a'

    code_names = ['mgw_reactor_tc_temperature', 'mgw_reactor_rtd_temperature']

    measurements = {}
    measurements[0] = TcReader(ports[0])
    measurements[0].start()
    measurements[1] = RtdReader(ports[1], measurements[0].value())
    measurements[1].start()

    loggers = {}
    loggers[code_names[0]] = ValueLogger(measurements[0], comp_val = 0.2, comp_type = 'lin')
    loggers[code_names[0]].start()
    loggers[code_names[1]] = ValueLogger(measurements[1], comp_val = 0.2, comp_type = 'lin')
    loggers[code_names[1]].start()

    datasocket = DateDataPullSocket('mgw_temp', code_names, timeouts=[2.0, 2.0], port=9001)
    datasocket.start()

    db_logger = ContinuousLogger(table='dateplots_mgw',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=code_names)

    db_logger.start()
    time.sleep(5)
    values = {}
    while True:
        time.sleep(1)
        for name in code_names:
            value = loggers[name].read_value()
            datasocket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(name + ': ' + str(value))
                db_logger.enqueue_point_now(name, value)
                loggers[name].clear_trigged()
