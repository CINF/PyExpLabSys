""" Data logger for mobile gas wall """
# pylint: disable=C0301,R0904, C0103

import threading
import logging
import time
import FindSerialPorts
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.sockets import LiveSocket
import PyExpLabSys.drivers.xgs600 as xgs600
import PyExpLabSys.drivers.omega_D6400 as D6400
import credentials


class PressureReader(threading.Thread):
    """ Communicates with the XGS controller """
    def __init__(self, xgs_instance):
        threading.Thread.__init__(self)
        self.xgs = xgs_instance
        self.chamberpressure = -9999
        self.quit = False

    def run(self):
        while not self.quit:
            time.sleep(2)
            pressures = self.xgs.read_all_pressures()
            self.chamberpressure = pressures[0]


class TemperatureReader(threading.Thread):
    """ Communicates with the Omega D6400 """
    def __init__(self, d6400_instance):
        threading.Thread.__init__(self)
        self.d6400 = d6400_instance
        self.temperatures = [float('NaN'),
                             self.d6400.read_value(1),
                             self.d6400.read_value(2),
                             self.d6400.read_value(3),
                             self.d6400.read_value(4),
                             self.d6400.read_value(5),
                             self.d6400.read_value(6),
                             self.d6400.read_value(7)]
        self.quit = False

    def run(self):
        while not self.quit:
            t = time.time()
            for i in range(1, 8):
                self.temperatures[i] = self.d6400.read_value(i)


class TemperatureLogger(threading.Thread):
    """ Read a specific temperature """
    def __init__(self, tempreader, channel, maximumtime=600):
        threading.Thread.__init__(self)
        self.tempreader = tempreader
        self.channel = channel
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
            time.sleep(2.5)
            self.value = self.tempreader.temperatures[self.channel]
            time_trigged = (time.time() - self.last_recorded_time) > self.maximumtime
            val_trigged = not (self.last_recorded_value - 1 < self.value < self.last_recorded_value + 1)
            if (time_trigged or val_trigged):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.value



class PressureLogger(threading.Thread):
    """ Read a specific XGS pressure """
    def __init__(self, xgsreader, channel, maximumtime=600):
        threading.Thread.__init__(self)
        self.xgsreader = xgsreader
        self.channel = channel
        self.pressure = None
        self.maximumtime = maximumtime
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False

    def read_pressure(self):
        """ Read the pressure """
        return(self.pressure)

    def run(self):
        while not self.quit:
            time.sleep(1)
            if self.channel == 0:
                self.pressure = self.xgsreader.chamberpressure
            if self.channel == 1:
                self.pressure = self.xgsreader.bufferpressure
            time_trigged = (time.time() - self.last_recorded_time) > self.maximumtime
            val_trigged = not (self.last_recorded_value * 0.9 < self.pressure < self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged) and (self.pressure > 0):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.pressure


if __name__ == '__main__':
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    omega = D6400.OmegaD6400(1, '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWECCJP-if00-port0')
    omega.update_range_and_function(1, action='tc', fullrange='K')
    omega.update_range_and_function(2, action='tc', fullrange='K')
    omega.update_range_and_function(3, action='tc', fullrange='K')
    omega.update_range_and_function(4, action='tc', fullrange='K')
    omega.update_range_and_function(5, action='tc', fullrange='K')
    omega.update_range_and_function(6, action='tc', fullrange='K')
    omega.update_range_and_function(7, action='tc', fullrange='K')

    xgs = xgs600.XGS600Driver('/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0')


    print xgs.read_all_pressures()

    pressurereader = PressureReader(xgs)
    pressurereader.daemon = True
    pressurereader.start()

    chamber_logger = PressureLogger(pressurereader, 0)
    chamber_logger.start()

    tempreader = TemperatureReader(omega)
    tempreader.daemon = True
    tempreader.start()

    temp_loggers = {}
    for i in range(0, 7):
        temp_loggers[i] = TemperatureLogger(tempreader, i + 1)
        temp_loggers[i].start()

    temp_codenames = ['vhp_T_reactor_inlet',
                      'vhp_T_reactor_outlet',
                      'vhp_T_reactor_top',
                      'vhp_T_mass_spec',
                      'vhp_T_gas_lines',
                      'vhp_T_purifying_reactor',
                      'vhp_T_furnace']

    socket = DateDataPullSocket('vhp', ['vhp_mass_spec_pressure'] + temp_codenames, timeouts=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])
    socket.start()

    db_logger = ContinuousLogger(table='dateplots_vhp_setup',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=['vhp_mass_spec_pressure'] + temp_codenames)
    db_logger.start()
    time.sleep(5)
    while True:
        time.sleep(0.25)
        for i in range(0, 7):
            t = temp_loggers[i].read_value()
            socket.set_point_now(temp_codenames[i], t)
            if temp_loggers[i].trigged:
                print t
                db_logger.enqueue_point_now(temp_codenames[i], t)
                temp_loggers[i].trigged = False

        c = chamber_logger.read_pressure()
        socket.set_point_now('vhp_mass_spec_pressure', c)
        if chamber_logger.trigged:
            print(c)
            db_logger.enqueue_point_now('vhp_mass_spec_pressure', c)
            chamber_logger.trigged = False
