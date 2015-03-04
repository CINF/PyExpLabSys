# pylint: disable=C0301,R0904, C0103
""" Data logger for mobile gas wall """

import threading
import logging
import socket as basic_socket
import time
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.xgs600 as xgs600
import credentials


class PressureReader(threading.Thread):
    """ Communicates with the XGS controller """
    def __init__(self, xgs_instance):
        threading.Thread.__init__(self)
        self.xgs = xgs_instance
        self.chamberpressure = -9999
        self.bufferpressure = -9999
        self.quit = False

    def value(self, channel):
        """ Return the value of the reader """
        if channel == 0:
            value = self.chamberpressure
        if channel == 1:
            value = self.bufferpressure
        return value

    def run(self):
        while not self.quit:
            time.sleep(1)
            try:
                pressures = self.xgs.read_all_pressures()
                self.chamberpressure = pressures[0]
                self.bufferpressure = pressures[1]
            except IndexError:
                print 'Av'

class ReactorReader(threading.Thread):
    """ Read reactor pressure from network """
    def __init__(self):
        threading.Thread.__init__(self)
        self.pressure = None
        self.quit = False

    def value(self):
        return self.pressure

    def run(self):
        """ Read the pressure """
        HOST, PORT = "10.54.7.24", 9998
        data = "read_flow_6 "
        # Error handling in this script is basically hopeless right now...
        while not self.quit:
            time.sleep(1)
            error = 1
            while error > 0:
                try:
                    sock = basic_socket.socket(basic_socket.AF_INET, basic_socket.SOCK_DGRAM)
                    sock.sendto(data + "\n", (HOST, PORT))
                    sock.settimeout(1)
                    received = sock.recv(1024)
                    error = 0
                except: # Timeout
                    error = error + 1
            try:
                self.pressure = 1000 * float(received)
            except ValueError:
                self.pressure = None

if __name__ == '__main__':
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)
    port = 'serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0'
    xgs = xgs600.XGS600Driver('/dev/' + port)
    print xgs.read_all_pressures()

    reader = PressureReader(xgs)
    reader.daemon = True
    reader.start()

    reactor_reader = ReactorReader()
    reactor_reader.daemon = True
    reactor_reader.start()

    time.sleep(2)

    reactor_logger = ValueLogger(reactor_reader, comp_val=5)
    chamber_logger = ValueLogger(reader, comp_val = 0.1, comp_type='log', channel = 0)
    buffer_logger = ValueLogger(reader, comp_val = 0.1, comp_type='log', channel = 1)
    chamber_logger.start()
    buffer_logger.start()
    reactor_logger.start()

    socket = DateDataPullSocket('mgw',
                                ['chamber_pressure', 'buffer_pressure'],
                                timeouts=[1.0, 1.0])
    socket.start()

    livesocket = LiveSocket('mgw', ['chamber_pressure', 'buffer_pressure'], 2)
    livesocket.start()

    db_logger = ContinuousLogger(table='dateplots_mgw',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=['mgw_pressure_chamber',
                                                        'mgw_pressure_buffer',
                                                        'mgw_reactor_pressure'])
    db_logger.start()
    time.sleep(5)
    while True:
        time.sleep(0.2)
        c = chamber_logger.read_value()
        b = buffer_logger.read_value()
        r = reactor_logger.read_value()
        socket.set_point_now('chamber_pressure', c)
        socket.set_point_now('buffer_pressure', b)
        livesocket.set_point_now('chamber_pressure', c)
        livesocket.set_point_now('buffer_pressure', b)

        if reactor_logger.read_trigged():
            print(r)
            db_logger.enqueue_point_now('mgw_reactor_pressure', r)
            reactor_logger.clear_trigged()

        if chamber_logger.read_trigged():
            print(c)
            db_logger.enqueue_point_now('mgw_pressure_chamber', c)
            chamber_logger.clear_trigged()

        if buffer_logger.read_trigged():
            print(b)
            db_logger.enqueue_point_now('mgw_pressure_buffer', b)
            buffer_logger.clear_trigged()


