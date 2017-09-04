""" Data logger for muffle furnace, chemlab 307 """
from __future__ import print_function
import threading
import time
import minimalmodbus
import serial
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class TemperatureReader(threading.Thread):
    """ Communicates with the Omega ?? """
    def __init__(self):
        port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWE9XWB-if00-port0'
        self.conn = minimalmodbus.Instrument(port, 1)
        self.conn.serial.baudrate = 9600
        self.conn.serial.parity = serial.PARITY_EVEN
        self.conn.serial.timeout = 0.25
        threading.Thread.__init__(self)
        self.temperature = 0
        self.quit = False

    def value(self):
        """ Return temperature """
        return self.temperature

    def run(self):
        while not self.quit:
            time.sleep(0.2)
            self.temperature = self.conn.read_register(4096, 1)


def main():
    """ Main function """
    tempreader = TemperatureReader()
    tempreader.daemon = True
    tempreader.start()

    temp_logger = ValueLogger(tempreader, comp_val=1)
    temp_logger.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_chemlab307',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=['chemlab307_muffle_furnace'])

    socket = DateDataPullSocket('muffle_furnace',
                                ['chemlab307_muffle_furnace'],
                                timeouts=[1.0])
    socket.start()

    livesocket = LiveSocket('muffle_furnace', ['chemlab307_muffle_furnace'])
    livesocket.start()

    db_logger.start()
    time.sleep(5)
    while True:
        time.sleep(0.25)
        value = temp_logger.read_value()
        socket.set_point_now('chemlab307_muffle_furnace', value)
        livesocket.set_point_now('chemlab307_muffle_furnace', value)
        if temp_logger.read_trigged():
            print(value)
            db_logger.save_point_now('chemlab307_muffle_furnace', value)
            temp_logger.clear_trigged()

if __name__ == '__main__':
    main()
