""" Data logger for the mobile gas wall """
# pylint: disable=C0301,R0904, C0103

import threading
import logging
import time
import minimalmodbus
import serial
import PyExpLabSys.drivers.agilent_34410A as dmm
import PyExpLabSys.auxiliary.rtd_calculator as rtd_calculator
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

    def run(self):
        while not self.quit:
            time.sleep(0.1)
            self.temperature = self.comm.read_register(4096, 1)

class RtdReader(threading.Thread):
    """ Communicates with the Omega ?? """
    def __init__(self, address, calib_temp):
        self.rtd_reader = dmm.Agilent34410ADriver(address, port='lan')
        self.rtd_reader.select_measurement_function('FRESISTANCE')
        self.calib_temp = calib_temp
        self.calib_value = self.rtd_reader.read()
        self.rtd_calc = rtd_calculator.RTD_Calculator(calib_temp, self.calib_value)
        threading.Thread.__init__(self)
        self.quit = False

    def run(self):
        while not self.quit:
            time.sleep(0.1)
            value = self.rtd_reader.read()
            self.temperature = self.rtd_calc.find_temperature(value)


class TemperatureLogger(threading.Thread):
    """ Read a specific temperature """
    def __init__(self, tempreader, maximumtime=600):
        threading.Thread.__init__(self)
        self.tempreader = tempreader
        self.value = None
        self.maximumtime = maximumtime
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False

    def read_value(self):
        """ Read the temperature """
        return(self.value)

    def run(self):
        while not self.quit:
            time.sleep(0.5)
            self.value = self.tempreader.temperature
            time_trigged = (time.time() - self.last_recorded_time) > self.maximumtime
            val_trigged = not (self.last_recorded_value - 0.3 < self.value < self.last_recorded_value + 0.3)
            if (time_trigged or val_trigged):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.value

if __name__ == '__main__':
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    socket_names = ['mgw_tc', 'mgw_rtd']
    logger_names = ['mgw_reactor_tc_temperature', 'mgw_reactor_rtd_temperature']
    datasocket = DateDataPullSocket('mgw_temp', socket_names, timeouts=[2.0, 2.0], port=9001)
    datasocket.start()

    db_logger = ContinuousLogger(table='dateplots_mgw',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=logger_names)

    ports = {}
    ports[1] = 'usb-FTDI_USB-RS485_Cable_FTWGRMCG-if00-port0'
    ports[2] = 'mobile-gaswall-agilent-34410a'
    measurements = {}
    loggers = {}

    measurements[1] = TcReader(ports[1])
    print measurements[1].temperature
    measurements[2] = RtdReader(ports[2], measurements[1].temperature)

    for i in [1, 2]:
        measurements[i].daemon = True
        measurements[i].start()
        loggers[i] = TemperatureLogger(measurements[i])
        loggers[i].start()

    db_logger.start()
    time.sleep(5)
    values = {}
    while True:
        time.sleep(0.1)
        for i in [1, 2]:
            values[i] = loggers[i].read_value()
            datasocket.set_point_now(socket_names[i-1], values[i])
            if loggers[i].trigged:
                print(logger_names[i-1] + str(i) + ': ' + str(values[i]))
                db_logger.enqueue_point_now(logger_names[i-1], values[i])
                loggers[i].trigged = False

