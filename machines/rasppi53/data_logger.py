""" Data logger for mobile gas wall """

import threading
import logging
import socket as basic_socket
import time

import FindSerialPorts
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.sockets import LiveSocket
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

    def run(self):
        while not self.quit:
            time.sleep(1)
            pressures = self.xgs.read_all_pressures()
            self.chamberpressure = pressures[0]
            self.bufferpressure = pressures[1]

class ReactorLogger(threading.Thread):
    """ Read reactor pressure from network and decides whether it is time to log """
    def __init__(self, maximumtime=600):
        threading.Thread.__init__(self)
        self.value = None
        self.maximumtime = maximumtime
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False

    def update_value(self):
        """ Read the pressure """
        HOST, PORT = "10.54.7.24", 9998
        data = "read_flow_6 "
        sock = basic_socket.socket(basic_socket.AF_INET, basic_socket.SOCK_DGRAM)
        sock.sendto(data + "\n", (HOST, PORT))
        received = sock.recv(1024)
        try:
            self.value = 1000 * float(received)
        except ValueError:
            self.value = None
        return(None)

    def run(self):
        while not self.quit:
            time.sleep(2.5)
            self.update_value()
            time_trigged = (time.time() - self.last_recorded_time) > self.maximumtime
            try:
                val_trigged = not (self.last_recorded_value * 0.9 < self.value < self.last_recorded_value * 1.1)
                val_trigged = val_trigged and (self.value > 0)
            except TypeError:
                val_trigged = False
            if (time_trigged or val_trigged) and (self.value is not None):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.value



class PressureLogger(threading.Thread):
    """ Read a specific XGS pressure """
    def __init__(self, xgsreader, channel, maximumtime=600):
        threading.Thread.__init__(self)
        self.xgsreader = xgsreader
        self.channel = channel
        self.pressure = None
        self.maximumtime = maximumtime
        self.bufferpressure = None
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False

    def read_pressure(self):
        """ Read the pressure """
        return(self.pressure)

    def run(self):
        while not self.quit:
            time.sleep(2.5)
            if self.channel == 0:
                self.pressure = self.xgsreader.chamberpressure
            if self.channel == 1:
                self.pressure = self.xgsreader.bufferpressure
            time_trigged = (time.time() - self.last_recorded_time) > self.maximumtime
            val_trigged = not (self.last_recorded_value * 0.9 < self.pressure < self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged) and (self.pressure > 0):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.pressure


if __name__ == '__main__':
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)
    port = 'serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0'
    xgs = xgs600.XGS600Driver('/dev/' + port)
    print xgs.read_all_pressures()

    reader = PressureReader(xgs)
    reader.daemon = True
    reader.start()

    reactor_logger = ReactorLogger(maximumtime=600)
    reactor_logger.start()

    chamber_logger = PressureLogger(reader, 0)
    buffer_logger = PressureLogger(reader, 1, maximumtime=1200)
    chamber_logger.start()
    buffer_logger.start()

    socket = DateDataPullSocket('mgw',['chamber_pressure', 'buffer_pressure'], timeouts=[1.0, 1.0])
    socket.start()

    #livesocket = LiveSocket(['chamber_pressure', 'buffer_pressure'], 2)
    #livesocket.start()

    db_logger = ContinuousLogger(table='dateplots_mgw', username=credentials.user, password=credentials.passwd, measurement_codenames=['mgw_pressure_chamber', 'mgw_pressure_buffer','mgw_reactor_pressure'])
    db_logger.start()
    time.sleep(5)
    while True:
        c = chamber_logger.read_pressure()
        b = buffer_logger.read_pressure()
        r = reactor_logger.value
        socket.set_point_now('chamber_pressure', c)
        socket.set_point_now('buffer_pressure', b)
        #livesocket.set_point_now('chamber_pressure', c)
        #livesocket.set_point_now('buffer_pressure', b)

        if reactor_logger.trigged:
            print(r)
            db_logger.enqueue_point_now('mgw_reactor_pressure', r)
            reactor_logger.trigged = False

        if chamber_logger.trigged:
            print(c)
            db_logger.enqueue_point_now('mgw_pressure_chamber', c)
            chamber_logger.trigged = False

        if buffer_logger.trigged:
            print(b)
            db_logger.enqueue_point_now('mgw_pressure_buffer', b)
            buffer_logger.trigged = False


