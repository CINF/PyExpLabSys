""" Pressure and temperature logger """
# pylint: disable=C0301,R0904, C0103

import threading
import time
import logging
import socket

from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataSocket
#from PyExpLabSys.common.sockets import LiveSocket
import PyExpLabSys.drivers.mks_925_pirani as mks_pirani
import PyExpLabSys.drivers.mks_pi_pc as mks_pipc



class PcClass(threading.Thread):
    """ Analog reader """
    def __init__(self):
        threading.Thread.__init__(self)
        self.pc = mks_pipc.Mks_Pi_Pc('/dev/ttyUSB0')
        self.pressure = None
        self.setpoint = 2000
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False

    def read_pressure(self):
        """ Read the pressure """
        return(self.pressure)

    def read_setpoint(self):
        """ Read the setpoint """
        return(self.setpoint)

    def update_setpoint(self):
        """ Read the setpoint from external socket server """
        HOST, PORT = "130.225.86.182", 9999
        data = "read_setpoint_pressure"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(data + "\n", (HOST, PORT))
        received = sock.recv(1024)
        setpoint = int(received)
        print setpoint
        self.set_setpoint(setpoint) 
        return(setpoint)

    def set_setpoint(self, setpoint):
        """ Set the setpoint """
        self.setpoint = setpoint
        return(True)

    def run(self):
        while not self.quit:
            time.sleep(0.5)
            self.pressure = self.pc.read_pressure()
            self.update_setpoint()
            self.pc.set_setpoint(self.setpoint)
            time_trigged = (time.time() - self.last_recorded_time) > 120
            val_trigged = not ((self.last_recorded_value * 0.9) < self.pressure < (self.last_recorded_value * 1.1))
            if (time_trigged or val_trigged):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.pressure


class PiraniClass(threading.Thread):
    """ Pressure reader """
    def __init__(self):
        threading.Thread.__init__(self)
        self.pirani = mks_pirani.mks_comm('/dev/ttyUSB1')
        self.pressure = None
        self.quit = False
        self.last_recorded_time = 0
        self.last_recorded_value = 0
        self.trigged = False

    def read_pressure(self):
        """ Read the pressure """
        return(self.pressure)

    def run(self):
        while not self.quit:
            time.sleep(1)
            self.pressure = self.pirani.read_pressure()
            time_trigged = (time.time() - self.last_recorded_time) > 120
            val_trigged = not (self.last_recorded_value * 0.9 < self.pressure < self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged) and (self.pressure > 0):
                self.trigged = True
                self.last_recorded_time = time.time()
                self.last_recorded_value = self.pressure

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

pc_measurement = PcClass()
pc_measurement.start()

pressure_measurement = PiraniClass()
pressure_measurement.start()

time.sleep(2)

datasocket = DateDataSocket(['pirani', 'pc'], timeouts=[1.0, 1.0])
datasocket.start()

db_logger = ContinuousLogger(table='dateplots_stm312', username='stm312', password='stm312', measurement_codenames=['stm312_pirani', 'stm312_pc'])
db_logger.start()

while True:
    pirani = pressure_measurement.read_pressure()
    pc = pc_measurement.read_pressure()
    datasocket.set_point_now('pirani', pirani)
    datasocket.set_point_now('pc', pc)
    if pressure_measurement.trigged:
        print(pirani)
        db_logger.enqueue_point_now('stm312_pirani', pirani)
        pressure_measurement.trigged = False

    if pc_measurement.trigged:
        print(pc)
        db_logger.enqueue_point_now('stm312_pc', pc)
        pc_measurement.trigged = False
