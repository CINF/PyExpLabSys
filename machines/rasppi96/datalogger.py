""" Pressure and temperature logger """
from __future__ import print_function
import threading
import time
import logging
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.mks_937b as mks_937b
import PyExpLabSys.drivers.mks_925_pirani as mks_925
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class Reader(threading.Thread):
    """ Pressure reader """
    def __init__(self, mks_937_instance, main_rough):
        threading.Thread.__init__(self)
        self.mks_937b = mks_937_instance
        self.main_rough = main_rough
        self.pressure = {}
        self.pressure['main_pirani'] = None
        self.pressure['main_baratron'] = None
        self.pressure['main_ion_gauge'] = None
        self.pressure['load_lock'] = None
        self.pressure['roughing_ll'] = None
        self.pressure['roughing_main'] = None
        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read values """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
            print('TTL failed')
            exit()
        else:
            if channel == 1:
                return_val = self.pressure['main_pirani']
            if channel == 2:
                return_val = self.pressure['main_baratron']
            if channel == 3:
                return_val = self.pressure['main_ion_gauge']
            if channel == 4:
                return_val = self.pressure['load_lock']
            if channel == 5:
                return_val = self.pressure['roughing_ll']
            if channel == 6:
                return_val = self.pressure['roughing_main']
        return return_val


    def run(self):
        while not self.quit:
            self.ttl = 150
            self.pressure['main_pirani'] = self.mks_937b.read_pressure_gauge(3)
            self.pressure['main_baratron'] = self.mks_937b.read_pressure_gauge(5)
            self.pressure['main_ion_gauge'] = self.mks_937b.read_pressure_gauge(1)
            self.pressure['load_lock'] = 0
            self.pressure['roughing_ll'] = 0
            self.pressure['roughing_main'] = self.main_rough.read_pressure()

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    mks_937b_instance = mks_937b.Mks937b('/dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0')
    mks_925_main_rough = mks_925.Mks925('/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTV9X8KH-if00-port0')
    reader = Reader(mks_937b_instance, mks_925_main_rough)
    reader.start()


    
    time.sleep(10)

    codenames = ['uhv_sputterchamber_pressure_pirani', 'uhv_sputterchamber_baratron_pressure',
                 'uhv_sputterchamber_pressure_iongauge', 'uhv_sputterchamber_ll_pressure',
                 'uhv_sputterchamber_ll_rough_pressure', 'uhv_sputterchamber_rough_pressure']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(reader, comp_val=0.01, low_comp=1e-3, maximumtime=600,
                                        comp_type='log', channel=1)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(reader, comp_val=0.001, low_comp=2e-4, maximumtime=600,
                                        comp_type='lin', channel=2)
    loggers[codenames[1]].start()
    loggers[codenames[2]] = ValueLogger(reader, comp_val=0.01, maximumtime=600, low_comp=1e-9,
                                        comp_type='log', channel=3)
    loggers[codenames[2]].start()
    loggers[codenames[3]] = ValueLogger(reader, comp_val=20, low_comp=1e-5, maximumtime=6000,
                                        comp_type='lin', channel=4)
    loggers[codenames[3]].start()
    loggers[codenames[4]] = ValueLogger(reader, comp_val=1.2, low_comp=1e-3, maximumtime=1200,
                                        comp_type='lin', channel=5)
    loggers[codenames[4]].start()
    loggers[codenames[5]] = ValueLogger(reader, comp_val=0.01, low_comp=1e-3, maximumtime=600,
                                        comp_type='log', channel=6)
    loggers[codenames[5]].start()


    livesocket = LiveSocket('UHV Sputterchamber pressures', codenames)
    livesocket.start()

    socket = DateDataPullSocket('UHV Sputterchamber pressures', codenames, 2)
    socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_uhv_sputterchamber',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    while reader.isAlive():
        time.sleep(1)
        for name in codenames:
            value = loggers[name].read_value()
            livesocket.set_point_now(name, value)
            socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(name + ': ' + str(value))
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    while True:
        try:
            main()
        except KeyboardInterrupt:
            print("Quitting")
            break
        except OSError as exception:  # Network error
            print("Got '{}'. Wait 5 min and restart.".format(exception))
            time.sleep(300)
