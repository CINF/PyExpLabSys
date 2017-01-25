""" Data logger for mobile gas wall """
from __future__ import print_function
import threading
import logging
import time
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.xgs600 as xgs600
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)


class PressureReader(threading.Thread):
    """ Communicates with the XGS controller """
    def __init__(self, xgs_instance):
        threading.Thread.__init__(self)
        self.xgs = xgs_instance
        self.containment = -9999
        self.bufferpressure = -9999
        self.quit = False

    def value(self, channel):
        """ Return the value of the reader """
        if channel == 0:
            value = self.containment
        if channel == 1:
            value = self.bufferpressure
        return value

    def run(self):
        while not self.quit:
            time.sleep(1)
            try:
                pressures = self.xgs.read_all_pressures()
                self.containment = pressures[0]
                self.bufferpressure = pressures[1]
            except IndexError:
                print('Av')

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)
    port = 'serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0'
    xgs = xgs600.XGS600Driver('/dev/' + port)
    print(xgs.read_all_pressures())

    reader = PressureReader(xgs)
    reader.daemon = True
    reader.start()

    buffer_logger = ValueLogger(reader, comp_val=0.1, comp_type='log',
                                channel=0, low_comp=1e-3)
    containment_logger = ValueLogger(reader, comp_val=0.1, comp_type='log',
                                     channel=1, low_comp=1e-3)
    buffer_logger.start()
    containment_logger.start()

    socket = DateDataPullSocket('mgw',
                                ['containment_pressure', 'buffer_pressure'],
                                timeouts=[1.0, 1.0])
    socket.start()

    livesocket = LiveSocket('mgw', ['containment_pressure', 'buffer_pressure'])
    livesocket.start()

    codenames = ['mgw_pressure_containment', 'mgw_pressure_buffer']
    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_mgw',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()
    time.sleep(5)

    while reader.isAlive():
        time.sleep(0.2)
        p_containment = containment_logger.read_value()
        p_buffer = buffer_logger.read_value()
        socket.set_point_now('containment_pressure', p_containment)
        socket.set_point_now('buffer_pressure', p_buffer)
        livesocket.set_point_now('containment_pressure', p_containment)
        livesocket.set_point_now('buffer_pressure', p_buffer)

        if containment_logger.read_trigged():
            print(p_containment)
            db_logger.save_point_now('mgw_pressure_containment', p_containment)
            containment_logger.clear_trigged()

        if buffer_logger.read_trigged():
            print(p_buffer)
            db_logger.save_point_now('mgw_pressure_buffer', p_buffer)
            buffer_logger.clear_trigged()

if __name__ == '__main__':
    main()
