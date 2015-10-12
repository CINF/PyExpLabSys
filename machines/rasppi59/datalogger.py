""" Data logger for the mobile gas wall """
# pylint: disable=C0301,R0904, C0103

import threading
import logging
import time
import minimalmodbus
import serial
#import PyExpLabSys.drivers.agilent_34410A as dmm
import PyExpLabSys.drivers.mks_925_pirani as mks925
import PyExpLabSys.drivers.mks_pi_pc as mkspc
import PyExpLabSys.drivers.omega_D6400 as D6400
#import PyExpLabSys.auxiliary.rtd_calculator as rtd_calculator
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
import credentials


class PressureReader(threading.Thread):
    """ Communicates with the Omega D6400 """
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.d6400 = D6400.OmegaD6400(1, port)
        for ch in range(1, 8):
            self.d6400.update_range_and_function(ch, action='voltage', fullrange='10')
        self.pressures = [float('NaN'),
                             self.d6400.read_value(1),
                             self.d6400.read_value(2),
                             self.d6400.read_value(3),
                             self.d6400.read_value(4),
                             self.d6400.read_value(5),
                             self.d6400.read_value(6),
                             self.d6400.read_value(7)]
        self.quit = False
        
    def convectorr(self, voltage):
        p = float(10**(voltage - 5.0)) * (1000.0/760.0) # mbar
        return p

    def igc25_iongauge(self, voltage):
        """ methode for calculating the ion gauge pressure of a IGC25 Ion Gauge from the analog voltage output"""
        p = 10**(0.8*voltage - 11) #mbar
        return p

    def igc25_pirani(self, voltage):
        #p = 10**(0.8*voltage - 5) #mbar
        #p = 1000.0 - 10**voltage
        #p(4v) = 1E-2 mbar
        p = voltage
        return p

    def value(self, channel):
        """ Return pressure of wanted channel """
        return(self.pressures[channel])

    def run(self):
        while not self.quit:
            time.sleep(0.5)
            for j in [1, 2, 3, 4]:
                self.pressures[j] = self.convectorr(self.d6400.read_value(j))
                #self.pressures[j] = self.d6400.read_value(j)
            for j in [5, 6]:
                self.pressures[j] = self.igc25_pirani(self.d6400.read_value(j))
                #self.pressures[j] = self.d6400.read_value(j)
            for j in [7,]:
                self.pressures[j] = self.igc25_iongauge(self.d6400.read_value(j))
                #self.pressures[j] = self.d6400.read_value(j)

class PiraniReader(threading.Thread):
    """ Communicates with the Omega D6400 """
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.mks925 = mks925.mks_comm(port)
        self.serial_no = self.mks925.read_serial()
        self.mks925.change_unit('MBAR')
        self.pressure = self.mks925.read_pressure()
        self.quit = False

    def value(self):
        """ Return pressure of wanted channel """
        return(self.pressure)

    def run(self):
        while not self.quit:
            time.sleep(0.5)
            self.pressure = (self.pressure + self.mks925.read_pressure() ) / 2.0


if __name__ == '__main__':
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    ports = {}
    ports[0] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTXQCCIT-if00-port0'
    ports[1] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTXQNRNZ-if00-port0'
    ports[2] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTXQQ07N-if00-port0'
    ports[3] = '/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTWR5F6W-if00-port0'
    codenames = ['stm312_hpc_baratron',
                 'stm312_prepump_loadlock',
                 'stm312_prepump_diff',
                 'stm312_prepump_bigturbo',
                 'stm312_prepump_gashandling',
                 'oldclustersource_prepump_aggregation',
                 'oldclustersource_prepump_quadrupole',
                 'oldclustersource_iongauge',
                 'oldclustersource_pirani',
                 'stm312_pc_pressure',
                 'stm312_pc_setpoint']
     #['stm312_hpc_pressure_controller','stm312_pirani']
     #Pullsocket = DateDataPullSocket('stm312 hpc pressure control', ['pressure', 'setpoint'])
     #Pushsocket = DataPushSocket('stm312 hpc pressure control', action='store_last')
    measurements = {}
    print '-starting measurements-'
    measurements[0] = PressureReader(ports[0])
    measurements[0].start()
    print '---'
    #measurements[1] = PiraniReader(ports[3])
    #measurements[1].start()

    loggers = {}
    #loggers[codenames[0]] = ValueLogger(measurements[2], comp_val = 1.5, comp_type = 'log')
    #loggers[codenames[0]].start()
    for i in range(1, 8):
        loggers[codenames[i]] = ValueLogger(measurements[0],
                                             comp_val = 1.5,
                                             comp_type = 'log',
                                             channel = i)
        loggers[codenames[i]].start()
    #loggers[codenames[8]] = ValueLogger(measurements[1], comp_val = 1.5, comp_type = 'log')
    #loggers[codenames[8]].start()

    datasocket = DateDataPullSocket('stm312_pressures', codenames, timeouts=[2.0] * len(codenames))
    datasocket.start()

    #db_logger = ContinuousLogger(table='dateplots_stm312',
    #                             username=credentials.user,
    #                             password=credentials.passwd,
    #                             measurement_codenames=code_names)
    #db_logger.start()
    
    time.sleep(2)
    values = {}
    while True:
        time.sleep(1)
        print '-- loop start --'
        for name in codenames[1:8]:
            value = loggers[name].read_value()
            print ("{}, value = {:.2e}".format(name, value))
            datasocket.set_point_now(name, value)
            #if loggers[name].read_trigged():
            #    print(name + ': ' + str(value))
            #    #db_logger.enqueue_point_now(name, value)
            #    loggers[name].clear_trigged()
    #for log in loggers.values():
    #    log.stop()
    for meas in measurements.values():
        meas.stop()
