""" Data logger for VHP """
from __future__ import print_function
import threading
import logging
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
import PyExpLabSys.drivers.xgs600 as xgs600
import PyExpLabSys.drivers.omega_D6400 as D6400
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class PressureReader(threading.Thread):
    """ Communicates with the XGS controller """
    def __init__(self, xgs_instance):
        threading.Thread.__init__(self)
        self.xgs = xgs_instance
        self.chamberpressure = None
        self.pc_backside = None
        self.quit = False

    def value(self, channel):
        """ Read the pressure """
        if channel == 0:
            return_val = self.chamberpressure
        if channel == 1:
            return_val = self.pc_backside
        return return_val

    def run(self):
        while not self.quit:
            time.sleep(5)
            pressures = self.xgs.read_all_pressures()
            self.chamberpressure = pressures[0]
            self.pc_backside = pressures[1]


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

    def value(self, channel):
        """ Read the temperatures """
        return self.temperatures[channel]

    def run(self):
        avg_length = 25
        while not self.quit:
            temperatures = [0] * 8
            for _ in range(0, avg_length):
                for index in range(1, 8):
                    temperatures[index] += self.d6400.read_value(index)
            for index in range(1, 8):
                self.temperatures[index] = temperatures[index] / avg_length


def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    omega = D6400.OmegaD6400(1, '/dev/serial/by-id/' +
                             'usb-FTDI_USB-RS485_Cable_FTWECCJP-if00-port0')
    omega.update_range_and_function(1, action='tc', fullrange='K')
    omega.update_range_and_function(2, action='tc', fullrange='K')
    omega.update_range_and_function(3, action='tc', fullrange='K')
    omega.update_range_and_function(4, action='tc', fullrange='K')
    omega.update_range_and_function(5, action='tc', fullrange='K')
    omega.update_range_and_function(6, action='tc', fullrange='K')
    omega.update_range_and_function(7, action='tc', fullrange='K')

    xgs = xgs600.XGS600Driver('/dev/serial/by-id/usb-Prolific_Technology_Inc.' +
                              '_USB-Serial_Controller_D-if00-port0')
    print(xgs.read_all_pressures())

    pressurereader = PressureReader(xgs)
    pressurereader.daemon = True
    pressurereader.start()

    tempreader = TemperatureReader(omega)
    tempreader.daemon = True
    tempreader.start()

    loggers = {}
    loggers['vhp_mass_spec_pressure'] = ValueLogger(pressurereader, comp_val=0.1,
                                                    low_comp=1e-11, comp_type='log',
                                                    channel=0)
    loggers['vhp_mass_spec_pressure'].start()

    loggers['vhp_pressure_pc_backside'] = ValueLogger(pressurereader, comp_val=0.1,
                                                      low_comp=1e-3, comp_type='log',
                                                      channel=1)
    loggers['vhp_pressure_pc_backside'].start()


    temp_codenames = ['vhp_T_reactor_inlet',
                      'vhp_T_reactor_outlet',
                      'vhp_T_reactor_top',
                      'vhp_T_mass_spec',
                      'vhp_T_gas_lines',
                      'vhp_T_purifying_reactor',
                      'vhp_T_furnace']

    for i in range(0, 7):
        loggers[temp_codenames[i]] = ValueLogger(tempreader, comp_val=0.2,
                                                 comp_type='lin', channel=i+1)
        loggers[temp_codenames[i]].start()

    all_codenames = ['vhp_mass_spec_pressure', 'vhp_pressure_pc_backside'] + temp_codenames
    socket = DateDataPullSocket('vhp', all_codenames, timeouts=1.0)
    socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_vhp_setup',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=all_codenames)
    db_logger.start()
    time.sleep(5)

    while tempreader.isAlive():
        time.sleep(0.5)
        for name in all_codenames:
            value = loggers[name].read_value()
            if loggers[name].read_trigged():
                print(value)
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()


if __name__ == '__main__':
    main()
