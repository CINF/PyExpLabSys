""" Data logger for the mobile gas wall """
from __future__ import print_function
import threading
import logging
import time
import minimalmodbus
import serial
import PyExpLabSys.drivers.agilent_34410A as dmm
import PyExpLabSys.drivers.omega_D6400 as D6400
import PyExpLabSys.drivers.srs_sr630 as sr630
import PyExpLabSys.auxiliary.rtd_calculator as rtd_calculator
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class SrsReader(threading.Thread):
    """ Communicates with SRS SR630 """
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.srs = sr630.SRS_SR630(port)
        self.temperatures = [float('NaN'),
                             self.srs.read_channel(1),
                             self.srs.read_channel(2),
                             self.srs.read_channel(3),
                             self.srs.read_channel(4),
                             self.srs.read_channel(5),
                             self.srs.read_channel(6),
                             self.srs.read_channel(7),
                             self.srs.read_channel(8),
                             self.srs.read_channel(9),
                             self.srs.read_channel(10),
                             self.srs.read_channel(11),
                             self.srs.read_channel(12),
                             self.srs.read_channel(13),
                             self.srs.read_channel(14),
                             self.srs.read_channel(15),
                             self.srs.read_channel(16)]
        self.quit = False

    def value(self, channel):
        """ Return temperature of wanted channel """
        return self.temperatures[channel]

    def run(self):
        while not self.quit:
            for j in range(1, 17):
                time.sleep(1)
                self.temperatures[j] = self.srs.read_channel(j)

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
        self.comm = minimalmodbus.Instrument(port, 1)
        self.comm.serial.baudrate = 9600
        self.comm.serial.parity = serial.PARITY_EVEN
        self.comm.serial.timeout = 0.5
        error = 0
        while error < 10:
            try:
                self.temperature = self.comm.read_register(4096, 1)
                break
            except OSError:
                error = error + 1
        if error > 9:
            exit('Error in communication with TC reader')
        threading.Thread.__init__(self)
        self.quit = False

    def value(self):
        """ Return current value of reader """
        if self.temperature < 1500:
            return self.temperature

    def run(self):
        while not self.quit:
            time.sleep(0.25)
            self.temperature = self.comm.read_register(4096, 1)

class RtdReader(threading.Thread):
    """ Read resistance of RTD and calculate temperature """
    def __init__(self, address, calib_temp):
        threading.Thread.__init__(self)
        self.rtd_reader = dmm.Agilent34410ADriver(interface='lan', hostname=address)
        self.rtd_reader.select_measurement_function('FRESISTANCE')
        #self.rtd_reader.select_measurement_function('RESISTANCE')
        self.calib_temp = calib_temp
        time.sleep(0.2)
        self.calib_value = self.rtd_reader.read()
        print('Room temperture resistance: ' + str(self.calib_value))
        self.temperature = None
        if self.calib_value < 1000:
            print(self.calib_value)
            self.rtd_calc = rtd_calculator.RTD_Calculator(calib_temp, self.calib_value)
            self.quit = False
        else:
            self.quit = True # Not a valid RTD

    def value(self):
        """ Return current value of reader """
        return self.temperature

    def run(self):
        while not self.quit:
            time.sleep(0.25)
            rtd_value = self.rtd_reader.read()
            temperature = self.rtd_calc.find_temperature(rtd_value)
            if temperature < 1000:
                self.temperature = temperature
            else:
                self.temperature = None

def main():
    """ Main fnuction """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    prefix = '/dev/serial/by-id/'
    ports = {}
#    ports[0] = prefix + 'usb-FTDI_USB-RS485_Cable_FTWGRMCG-if00-port0'
#    ports[1] = 'mobile-gaswall-agilent-34410a'
    ports[2] = prefix + 'usb-FTDI_USB-RS485_Cable_FTWGUBYN-if00-port0'
#    ports[3] = prefix + 'usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
    code_names = [#'mgw_reactor_tc_temperature',
                  #'mgw_reactor_rtd_temperature',
                  'mgw_omega_temp_ch01',
                  'mgw_omega_temp_ch02',
                  'mgw_omega_temp_ch03',
                  'mgw_omega_temp_ch04',
                  'mgw_omega_temp_ch05',
                  'mgw_omega_temp_ch06',
                  'mgw_omega_temp_ch07',
                  #'mgw_sr630_temp_01',
                  #'mgw_sr630_temp_02',
                  #'mgw_sr630_temp_03',
                  #'mgw_sr630_temp_04',
                  #'mgw_sr630_temp_05',
                  #'mgw_sr630_temp_06',
                  #'mgw_sr630_temp_07',
                  #'mgw_sr630_temp_08',
                  #'mgw_sr630_temp_09',
                  #'mgw_sr630_temp_10',
                  #'mgw_sr630_temp_11',
                  #'mgw_sr630_temp_12',
                  #'mgw_sr630_temp_13',
                  #'mgw_sr630_temp_14',
                  #'mgw_sr630_temp_15',
                  #'mgw_sr630_temp_16'
]

    measurements = {}
#    measurements[0] = TcReader(ports[0])
#    measurements[0].start()
#    measurements[1] = RtdReader(ports[1], measurements[0].value())
#    measurements[1].start()
    measurements[2] = TemperatureReader(ports[2])
    measurements[2].start()
#    measurements[3] = SrsReader(ports[3])
#    measurements[3].start()

    loggers = {}
#    loggers[code_names[0]] = ValueLogger(measurements[0], comp_val=1.5,
#                                         comp_type='lin', low_comp=0)
#    loggers[code_names[0]].start()
#    loggers[code_names[1]] = ValueLogger(measurements[1], comp_val=0.5,
#                                         comp_type='lin', low_comp=0)
#    loggers[code_names[1]].start()
#    for i in range(2, 9):
    for i in range(0,len(code_names)):
        loggers[code_names[i]] = ValueLogger(measurements[2], comp_val=1.0,
                                             comp_type='lin', channel=i-1)
        loggers[code_names[i]].start()
        print(loggers[code_names[i]])
#    for i in range(9, 25):
#        print('Channel: ' + str(i-8) + ' , codename: ' + code_names[i])
#        loggers[code_names[i]] = ValueLogger(measurements[3], comp_val=0.3,
#                                             comp_type='lin', channel=i-8)
#        loggers[code_names[i]].start()
#        print(loggers[code_names[i]])
    datasocket = DateDataPullSocket('mgw_tmp', code_names, timeouts=4, port=9000)
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
            print(name + ': ' + str(value) + str(loggers[name].read_trigged()))

            if loggers[name].read_trigged():
                print(name + ': ' + str(value))
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
