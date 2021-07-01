""" Pressure and temperature logger """
from __future__ import print_function
import threading
import time
import logging
import socket
import numpy as np # pylint: disable=import-error
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.dataq_comm as dataq
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class SocketReaderClass(threading.Thread):
    """ Read the wanted socket """
    def __init__(self):
        threading.Thread.__init__(self)
        self.current_value = None
        self.quit = False

    def value(self):
        """ return current value """
        return self.current_value

    def run(self):
        while not self.quit:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            try:
                sock.sendto(b'read_pressure', ('10.54.6.118', 9995))
                received = sock.recv(1024)
                received = received.decode('ascii')
                self.current_value = float(received)
            except (socket.timeout, ValueError) as e:
                print(e) # LOG THIS
            time.sleep(1)

class SocketReaderClassPC(threading.Thread):
    """ Read the wanted socket """
    def __init__(self):
        threading.Thread.__init__(self)
        self.current_value = None
        self.quit = False

    def value(self):
        """ return current value """
        return self.current_value

    def run(self):
        while not self.quit:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            try:
                sock.sendto(b'M17214588A#raw', ('10.54.7.24', 9000))
                received = sock.recv(1024)
                received = received.decode('ascii')
                value = received[received.find(',')+1:]
                self.current_value = float(value)
            except (socket.timeout, ValueError) as e:
                print(e) # LOG THIS
            time.sleep(1)
            print('PC Value: ' + str(value))


class Reader(threading.Thread):
    """ Pressure reader """
    def __init__(self, dataq_instance):
        threading.Thread.__init__(self)
        self.dataq = dataq_instance
        self.pressure = {}
        self.pressure['medium'] = None
        self.pressure['high'] = None
        self.pressure['bpr'] = None
        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read values """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel == 1:
                return_val = self.pressure['medium']
            if channel == 2:
                return_val = self.pressure['high']
            if channel == 3:
                return_val = self.pressure['bpr']
        return return_val

    def run(self):
        while not self.quit:
            self.ttl = 50
            values = np.zeros(3)
            average_length = 10
            for _ in range(0, average_length):
                measurements = self.dataq.read_measurements()
                values[0] += measurements[1]
                values[1] += measurements[2]
                values[2] += measurements[3]
            values = values / average_length
            self.pressure['medium'] = (1.0/5) * (values[0] - 0.1) * 7910.55729 - 15.8
            self.pressure['high'] = (1.0/5) * (values[1] - 0.1) * 206842.719
            self.pressure['bpr'] = (-1.0/10) * values[2] * 2068.42719
            time.sleep(0.2)

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    socket_reader = SocketReaderClass()
    socket_reader.start()

    socket_reader_pc = SocketReaderClassPC()
    socket_reader_pc.start()

    dataq_instance = dataq.DataQ('/dev/serial/by-id/usb-0683_1550-if00')
    dataq_instance.add_channel(1)
    dataq_instance.add_channel(2)
    dataq_instance.add_channel(3)
    dataq_instance.start_measurement()
    reader = Reader(dataq_instance)
    reader.start()

    time.sleep(2.5)

    codenames = ['vhp_medium_pressure', 'vhp_high_pressure', 'vhp_pressure_bpr_backside',
                 'vhp_low_pressure', 'vhp_pressure_controller']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(reader, comp_val=20, maximumtime=600,
                                        comp_type='lin', channel=1)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(reader, comp_val=500, maximumtime=600,
                                        comp_type='lin', channel=2)
    loggers[codenames[1]].start()
    loggers[codenames[2]] = ValueLogger(reader, comp_val=20, maximumtime=600,
                                        comp_type='lin', channel=3)
    loggers[codenames[2]].start()

    loggers[codenames[3]] = ValueLogger(socket_reader, comp_val=0.01, maximumtime=300,
                                        comp_type='log')
    loggers[codenames[3]].start()
    loggers[codenames[4]] = ValueLogger(socket_reader_pc, comp_val=1, maximumtime=300,
                                        comp_type='lin')
    loggers[codenames[4]].start()

    livesocket = LiveSocket('VHP Gas system pressure', codenames)
    livesocket.start()

    pull_socket = DateDataPullSocket('VHP Gas system pressure', codenames,
                                     timeouts=[2.0] * len(loggers))
    pull_socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_vhp_setup',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    while reader.isAlive():
        time.sleep(1)
        for name in codenames:
            value = loggers[name].read_value()
            livesocket.set_point_now(name, value)
            pull_socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(name + ': ' + str(value))
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
