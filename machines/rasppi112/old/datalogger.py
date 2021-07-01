""" Data logger for the PVD309 effusion cells """
import threading
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.utilities import get_logger
import PyExpLabSys.drivers.omega_cni as omega_cni
import PyExpLabSys.drivers.omega_cn7800 as omega_cn7800
import credentials

LOGGER = get_logger('PVD309', level='info', file_log=True,
                    file_name='pvd309_effusion_log.txt', terminal_log=False)

class TemperatureReader(threading.Thread):
    """ Communicates with the Omega Controllers """
    def __init__(self):
        cn7800_port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTY0VXC8-if00-port0' 
        self.cn7800 = omega_cn7800.CN7800(cn7800_port)
        self.temp_mai = self.cn7800.read_temperature()
        cni_port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTY0EQZZ-if00-port0'
        self.cni = omega_cni.ISeries(cni_port, 9600, comm_stnd='rs485')
        self.temp_dca = self.cni.read_temperature(1)
        threading.Thread.__init__(self)
        self.quit = False
        self.ttl = 10

    def value(self, channel):
        """ Return current value of reader """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        if channel == 1:
            return self.temp_dca
        if channel == 2:
            return self.temp_mai

    def run(self):
        while not self.quit:
            time.sleep(0.1)
            self.temp_mai = self.cn7800.read_temperature()
            self.temp_dca = self.cni.read_temperature(1)
            self.ttl = 10

def main():
    """ Main function """
    code_names = ['pvd309_temp_dca_cell', 'pvd309_temp_mai_cell']

    reader = TemperatureReader()
    reader.start()
    
    loggers = {}
    loggers[code_names[0]] = ValueLogger(reader, channel=1, comp_val = 0.5, comp_type = 'lin')
    loggers[code_names[0]].start()
    loggers[code_names[1]] = ValueLogger(reader, channel=2, comp_val = 0.5, comp_type = 'lin')
    loggers[code_names[1]].start()

    datasocket = DateDataPullSocket('pvd_309_temp', code_names, timeouts=[2.0] * 2, port=9001)
    datasocket.start()
    livesocket = LiveSocket('pvd_309_temperatures', code_names)
    livesocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_pvd309',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=code_names)
    db_logger.start()
    time.sleep(5)
    while not reader.quit:
        time.sleep(0.25)
        for name in code_names:
            print(reader.ttl)
            value = loggers[name].read_value()
            datasocket.set_point_now(name, value)
            livesocket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(name + ': ' + str(value))
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()


if __name__ == '__main__':
    main()
