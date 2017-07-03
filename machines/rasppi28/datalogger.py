""" Pressure and temperature logger PS"""
from __future__ import print_function
import threading
import time
import logging
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
#from PyExpLabSys.common.sockets import LiveSocket
import PyExpLabSys.drivers.xgs600 as xgs600
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class PressureReader(threading.Thread):
    """ Pressure reader """
    def __init__(self, xgs):
        threading.Thread.__init__(self)
        self.xgs = xgs
        self.main = None
        self.qms = None
        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel == 0:
                return_val = self.qms
            if channel == 1:
                return_val = self.main
        return return_val

    def run(self):
        while not self.quit:
            press = self.xgs.read_all_pressures()
            try:
                if not self.quit:
                    self.qms = press[0]
                    self.main = press[1]
                    self.ttl = 50
            except IndexError:
                print("av")
            time.sleep(5)

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    ports = '/dev/serial/by-id/'
    ports += 'usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
    xgs_instance = xgs600.XGS600Driver(ports)
    print(xgs_instance.read_all_pressures())

    pressure = PressureReader(xgs_instance)
    pressure.start()

    time.sleep(2.5)

    codenames = ['ps_qms_pressure', 'ps_chamber_pressure']
    loggers = {}
    loggers[codenames[0]] = ValueLogger(pressure, comp_val=0.1, low_comp=1e-11,
                                        comp_type='log', channel=0)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(pressure, comp_val=0.1, low_comp=1e-11,
                                        comp_type='log', channel=1)
    loggers[codenames[1]].start()

    #livesocket = LiveSocket('PS', codenames, 2)
    #livesocket.start()

    socket = DateDataPullSocket('PS pressure logger',
                                codenames, timeouts=2 * [1.0], port=9001)
    socket.start()


    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_ps',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    while pressure.isAlive():
        time.sleep(0.5)
        for name in codenames:
            value = loggers[name].read_value()
            #livesocket.set_point_now(name, value)
            socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(value)
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
