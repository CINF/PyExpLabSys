""" Data logger for the mobile gas wall """
from __future__ import print_function
import threading
import logging
import time
import minimalmodbus
import serial
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

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

def main():
    """ Main fnuction """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTY5BU0H-if00-port0'
    code_name = 'omicron_tpd_temperature'

    measurement = TcReader(port)
    measurement.start()

    logger = ValueLogger(measurement, comp_val=0.25, comp_type='lin')
    logger.start()

    datasocket = DateDataPullSocket('mgw_temp', [code_name], timeouts=4, port=9000)
    datasocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_omicron',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=[code_name])
    db_logger.start()

    time.sleep(5)

    while measurement.isAlive():
        time.sleep(1)
        value = logger.read_value()
        datasocket.set_point_now(code_name, value)

        if logger.read_trigged():
            print(code_name + ': ' + str(value))
            db_logger.save_point_now(code_name, value)
            logger.clear_trigged()

if __name__ == '__main__':
    main()
