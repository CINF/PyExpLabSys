""" Data logger for mobile gas wall """
from __future__ import print_function
import threading
import logging
import socket as basic_socket
import time
from PyExpLabSys.common.database_saver import ContinuousDataSaver
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
                print('Av')

class ReactorReader(threading.Thread):
    """ Read reactor pressure from network """
    def __init__(self):
        threading.Thread.__init__(self)
        self.pressure = None
        self.quit = False

    def value(self):
        """ Return current nummeric value """
        return self.pressure

    def run(self):
        """ Read the pressure """
        host, port = "10.54.7.24", 9000
        data = "M11200362H#raw"
        while not self.quit:
            time.sleep(1)
            error = 1
            while error > 0:
                try:
                    sock = basic_socket.socket(basic_socket.AF_INET, basic_socket.SOCK_DGRAM)
                    sock.sendto(data.encode('ascii'), (host, port))
                    sock.settimeout(1)
                    received = sock.recv(1024)
                    received = received.decode()
                    error = 0
                except basic_socket.timeout:
                    error = error + 1
                    time.sleep(0.1)
            try:
                self.pressure = 1000 * float(received[received.find(',')+1:])
            except ValueError:
                self.pressure = None

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

    reactor_reader = ReactorReader()
    reactor_reader.daemon = True
    reactor_reader.start()

    time.sleep(2)

    reactor_logger = ValueLogger(reactor_reader, comp_val=5)
    chamber_logger = ValueLogger(reader, comp_val=0.1, comp_type='log',
                                 channel=0, low_comp=1e-3)
    buffer_logger = ValueLogger(reader, comp_val=0.1, comp_type='log',
                                channel=1, low_comp=1e-3)
    chamber_logger.start()
    buffer_logger.start()
    reactor_logger.start()

    socket = DateDataPullSocket('mgw',
                                ['chamber_pressure', 'buffer_pressure'],
                                timeouts=[1.0, 1.0])
    socket.start()

    livesocket = LiveSocket('mgw', ['chamber_pressure', 'buffer_pressure'], 2)
    livesocket.start()

    codenames = ['mgw_pressure_chamber', 'mgw_pressure_buffer', 'mgw_reactor_pressure']
    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_mgw',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()
    time.sleep(5)

    while reader.isAlive():
        time.sleep(0.2)
        p_chamber = chamber_logger.read_value()
        p_buffer = buffer_logger.read_value()
        p_reactor = reactor_logger.read_value()
        socket.set_point_now('chamber_pressure', p_chamber)
        socket.set_point_now('buffer_pressure', p_buffer)
        livesocket.set_point_now('chamber_pressure', p_chamber)
        livesocket.set_point_now('buffer_pressure', p_buffer)

        if reactor_logger.read_trigged():
            print(p_reactor)
            db_logger.save_point_now('mgw_reactor_pressure', p_reactor)
            reactor_logger.clear_trigged()

        if chamber_logger.read_trigged():
            print(p_chamber)
            db_logger.save_point_now('mgw_pressure_chamber', p_chamber)
            chamber_logger.clear_trigged()

        if buffer_logger.read_trigged():
            print(p_buffer)
            db_logger.save_point_now('mgw_pressure_buffer', p_buffer)
            buffer_logger.clear_trigged()

if __name__ == '__main__':
    main()
