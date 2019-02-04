""" Pressure and temperature logger """
from __future__ import print_function
import threading
import time
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.xgs600 as xgs600
import PyExpLabSys.drivers.agilent_34972A as agilent_34972A
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class MuxReader(threading.Thread):
    """ Analog reader """
    def __init__(self, mux):
        threading.Thread.__init__(self)
        self.mux = mux
        self.ttl = 20
        self.temperature = None
        self.quit = False

    def value(self):
        """ Read the temperaure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        return self.temperature

    def run(self):
        while not self.quit:
            self.ttl = 20
            time.sleep(1)
            mux_list = self.mux.read_single_scan()
            self.temperature = mux_list[0]

class PressureReader(threading.Thread):
    """ Pressure reader """
    def __init__(self, xgs):
        threading.Thread.__init__(self)
        self.xgs = xgs
        self.pressure = None
        self.quit = False
        self.ttl = 20

    def value(self):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        return self.pressure

    def run(self):
        while not self.quit:
            self.ttl = 20
            time.sleep(0.5)
            press = self.xgs.read_all_pressures()
            try:
                self.pressure = press[0]
            except IndexError:
                print("av")
                self.pressure = 0

def main():
    """ Main code """
    #mux_instance = agilent_34972A.Agilent34972ADriver(interface='lan', hostname='volvo-agilent-34972a')
    port = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'
    xgs_instance = xgs600.XGS600Driver(port)

    #analog_measurement = MuxReader(mux_instance)
    #analog_measurement.start()

    pressure = PressureReader(xgs_instance)
    print('-')
    pressure.start()

    time.sleep(2.5)

    #codenames = ['volvo_pressure', 'volvo_temperature']
    codenames = ['volvo_pressure']
    loggers = {}
    loggers[codenames[0]] = ValueLogger(pressure, comp_val=0.1, comp_type='log', low_comp=1e-9)
    loggers[codenames[0]].start()
    #loggers[codenames[1]] = ValueLogger(analog_measurement, comp_val=0.5, comp_type='lin')
    #loggers[codenames[1]].start()

    socket = DateDataPullSocket('Volvo data logger', codenames, timeouts=1.0)
    socket.start()

    livesocket = LiveSocket('Volvo data logger', codenames)
    livesocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_volvo',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    #while pressure.isAlive() and analog_measurement.isAlive():
    while True:
        time.sleep(0.25)
        for name in codenames:
            value = loggers[name].read_value()
            socket.set_point_now(name, value)
            livesocket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(value)
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    while True:
        try:
            main()
        except KeyboardInterrupt:
            break
        except OSError as exception:
            print("Got '{}'. Waiting 5 min and run again".format(exception))
            time.sleep(300)

