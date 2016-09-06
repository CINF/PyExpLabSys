""" Data logger for the mobile gas wall """
from __future__ import print_function
import threading
import logging
import time
import minimalmodbus
import serial
import PyExpLabSys.drivers.agilent_34410A as dmm
import PyExpLabSys.drivers.omega_D6400 as D6400
import PyExpLabSys.auxiliary.rtd_calculator as rtd_calculator
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
import credentials


class TemperatureReader(threading.Thread):
    """ Communicates with the Omega D6400 """
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.d6400 = D6400.OmegaD6400(1, port)
        self.d6400.update_range_and_function(1, action='tc', fullrange='K')
        self.d6400.update_range_and_function(2, action='tc', fullrange='K')
        self.d6400.update_range_and_function(3, action='tc', fullrange='K')
        self.d6400.update_range_and_function(4, action='tc', fullrange='K')
        self.d6400.update_range_and_function(5, action='tc', fullrange='K')
        self.d6400.update_range_and_function(6, action='tc', fullrange='K')
        self.d6400.update_range_and_function(7, action='tc', fullrange='K')
        self.temperatures = [float('NaN'),
                             self.d6400.read_value(1),
                             self.d6400.read_value(2),
                             self.d6400.read_value(3),
                             self.d6400.read_value(4),
                             self.d6400.read_value(5),
                             self.d6400.read_value(6),
                             self.d6400.read_value(7)]
        self.quit = False

    def value(self, channel):
        """ Return temperature of wanted channel """
        return self.temperatures[channel]

    def run(self):
        while not self.quit:
            time.sleep(0.5)
            for j in range(1, 8):
                self.temperatures[j] = (self.temperatures[j] + self.d6400.read_value(j)) / 2.0


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
        if self.temperature < 1500:
            return self.temperature

    def run(self):
        while not self.quit:
            time.sleep(0.1)
            self.temperature = self.comm.read_register(4096, 1)

class RtdReader(threading.Thread):
    """ Read resistance of RTD and calculate temperature """
    def __init__(self, address, calib_temp):
        self.rtd_reader = dmm.Agilent34410ADriver(interface='lan', hostname=address)
        self.rtd_reader.select_measurement_function('FRESISTANCE')
        #self.rtd_reader.select_measurement_function('RESISTANCE')
        self.calib_temp = calib_temp
        time.sleep(0.2)
        self.calib_value = self.rtd_reader.read()
        print(self.calib_value)
        self.rtd_calc = rtd_calculator.RTD_Calculator(calib_temp, self.calib_value)
        threading.Thread.__init__(self)
        self.temperature = None
        self.quit = False

    def value(self):
        """ Return current value of reader """
        return self.temperature

    def run(self):
        while not self.quit:
            time.sleep(0.1)
            rtd_value = self.rtd_reader.read()
            self.temperature = self.rtd_calc.find_temperature(rtd_value)

def main():
    """ Main fnuction """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    ports = {}
    ports[0] = 'usb-FTDI_USB-RS485_Cable_FTWGRMCG-if00-port0'
    ports[1] = 'mobile-gaswall-agilent-34410a'
    ports[2] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWBEDQ3-if00-port0'
    ports[3] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWGUBYN-if00-port0'
    code_names = ['mgw_reactor_tc_temperature',
                  'mgw_reactor_rtd_temperature',
                  'mgw_omega_temp_ch01',
                  'mgw_omega_temp_ch02',
                  'mgw_omega_temp_ch03',
                  'mgw_omega_temp_ch04',
                  'mgw_omega_temp_ch05',
                  'mgw_omega_temp_ch06',
                  'mgw_omega_temp_ch07',
                  'mgw_omega_temp_ch08',
                  'mgw_omega_temp_ch09',
                  'mgw_omega_temp_ch10',
                  'mgw_omega_temp_ch11',
                  'mgw_omega_temp_ch12',
                  'mgw_omega_temp_ch13',
                  'mgw_omega_temp_ch14']

    measurements = {}
    measurements[0] = TcReader(ports[0])
    measurements[0].start()
    measurements[1] = RtdReader(ports[1], measurements[0].value())
    measurements[1].start()
    measurements[2] = TemperatureReader(ports[2])
    measurements[2].start()
    measurements[3] = TemperatureReader(ports[3])
    measurements[3].start()

    loggers = {}
    loggers[code_names[0]] = ValueLogger(measurements[0], comp_val=1.5, comp_type='lin')
    loggers[code_names[0]].start()
    loggers[code_names[1]] = ValueLogger(measurements[1], comp_val=0.5, comp_type='lin')
    loggers[code_names[1]].start()
    for i in range(2, 9):
        loggers[code_names[i]] = ValueLogger(measurements[2], comp_val=1.0,
                                             comp_type='lin', channel=i-1)
        loggers[code_names[i]].start()
    for i in range(9, 16):
        loggers[code_names[i]] = ValueLogger(measurements[3], comp_val=2.0,
                                             comp_type='lin', channel=i-8)
        loggers[code_names[i]].start()

    datasocket = DateDataPullSocket('mgw_temp', code_names, timeouts=[2.0] * 16, port=9001)
    datasocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_mgw',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=code_names)

    db_logger.start()
    time.sleep(5)
    while True:
        time.sleep(1)
        for name in code_names:
            value = loggers[name].read_value()
            datasocket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(name + ': ' + str(value))
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
