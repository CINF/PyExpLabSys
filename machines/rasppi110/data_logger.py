""" Pressure data logger for XRD """
from __future__ import print_function
import threading
import time
import PyExpLabSys.drivers.edwards_agc as EdwardsAGC
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.utilities import get_logger
import credentials

class PressureReader(threading.Thread):
    """ Read XRD pressure gauges"""
    def __init__(self, port):
        threading.Thread.__init__(self)
        self.eagc = EdwardsAGC.EdwardsAGC(port)
        self.gas_turbo = -1
        self.gas_system_wrg = -1
        self.mass_spectrometer = -1
        self.gas_system_baratron = -1
        self.quit = False

    def value(self, channel):
        """ Return the value of the reader """
        if channel == 1:
            value = self.gas_turbo
        if channel == 2:
            value = self.gas_system_wrg
        if channel == 3:
            value = self.mass_spectrometer
        if channel == 4:
            value = self.gas_system_baratron
        return value

    def run(self):
        while not self.quit:
            time.sleep(1)
            self.gas_turbo = self.eagc.read_pressure(1)
            self.gas_system_wrg = self.eagc.read_pressure(2)
            self.mass_spectrometer = self.eagc.read_pressure(3)
            self.gas_system_baratron = self.eagc.read_pressure(4)

def main():
    """ Main function """
    log = get_logger('pressure readout', level='debug')
    #logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    #logging.basicConfig(level=logging.ERROR)

    port = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port'
    port = '/dev/ttyUSB0'
    codenames = ['xrd_pressure_turbo_gas_system', 'xrd_pressure_gas_system_wrg',
                 'xrd_pressure_mass_spec_wrg', 'xrd_pressure_gas_system_baratron']
    reader = PressureReader(port)
    reader.daemon = True
    reader.start()

    loggers = {}
    loggers[codenames[0]] = ValueLogger(reader, comp_val=0.02, comp_type='log', channel=1)
    loggers[codenames[1]] = ValueLogger(reader, comp_val=0.02, comp_type='log', channel=2)
    loggers[codenames[2]] = ValueLogger(reader, comp_val=0.02, comp_type='log', channel=3)
    loggers[codenames[3]] = ValueLogger(reader, comp_val=2, comp_type='lin', channel=4)

    for i in range(0, 4):
        loggers[codenames[i]].start()

    socket = DateDataPullSocket('XRD Pressure', codenames, timeouts=[2.0] * len(codenames))
    socket.start()
    log.info('DateDataPullSocket started')
    live_socket = LiveSocket('XRD pressure', codenames)
    live_socket.start()
    log.info('LiveSocket started')

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_xrd',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()
    log.info('ContinuousDataSaver started')

    time.sleep(5)

    try:
        while True:
            time.sleep(0.25)
            for name in codenames:
                value = loggers[name].read_value()
                log.debug('Read codename %s value %s', name, value)
                socket.set_point_now(name, value)
                live_socket.set_point_now(name, value)
                if loggers[name].read_trigged():
                    log.debug('Saved codename %s value %s', name, value)
                    db_logger.save_point_now(name, value)
                    loggers[name].clear_trigged()
    except KeyboardInterrupt:
        log.info('Stopping everything and waiting 5 s')
        socket.stop()
        live_socket.stop()
        db_logger.stop()
        time.sleep(5)
        log.info('Everything stopped, bye!')
    except Exception:
        # Unexpected exception, log it
        log.exception('Unexpected exception during main loop')
        raise

if __name__ == '__main__':
    main()
