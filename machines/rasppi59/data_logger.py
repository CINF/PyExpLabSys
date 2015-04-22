""" measure and logging of the pressure in the
stm312 high pressure cell, range 0-10mbar
"""
# pylint: disable=C0301,R0904, C0103

import threading
import logging
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
import PyExpLabSys.drivers.omega_D6400 as omega_D6400
import PyExpLabSys.drivers.mks_pi_pc as mks_pi_pc
import PyExpLabSys.drivers.mks_925_pirani as mks_925_pirani

import credentials

class PressurePiraniReader(threading.Thread):
    """ Read Cooling water pressure """
    def __init__(self, omega, channel):
        threading.Thread.__init__(self)
        self.omega = omega
        self.pressure = -1
        self.quit = False

    def value(self):
        """ Return the value of the reader """
        return(self.pressure)

    def run(self):
        while not self.quit:
            time.sleep(1)
            self.pressure = self.omega.read_value(1)

#logging.basicConfig(filename="logger.txt", level=logging.ERROR)
#logging.basicConfig(level=logging.ERROR)

port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWE9PXJ-if00-port0'
omega_instance = omega_D6400.OmegaD6400(address=1, port=port)
piranis = []
pressurereader = PressureReader(omega_instance)
pressurereader.daemon = True
pressurereader.start()

logger = ValueLogger(pressurereader, comp_val=0.1)
logger.start()


name = 'stm312_pressure'
codenames = ['stm312_hpc_baratron',
             'stm312_prepump_bigturbo',
             'stm312_prepump_gashandling',
             'stm312_prepump_diff',
             'stm312_prepump_loadlock',
             'oldclustersource_prepump_aggregation',
             'oldclustersource_prepump_quadrupole',
             'oldclustersource_iongauge',
             'oldclustersource_pirani']
socket = DateDataPullSocket(name, codenames, timeouts=[1.0])
socket.start()

live_socket = LiveSocket(name, codenames, 2)
live_socket.start()

db_logger = ContinuousLogger(table='dateplots_stm312',
                             username=credentials.user,
                             password=credentials.passwd,
                             measurement_codenames=codenames)
db_logger.start()

time.sleep(2)

while True:
    time.sleep(0.25)
    p = logger.read_value()
    socket.set_point_now('stm312_hpc_baratron', p)
    live_socket.set_point_now('stm312_hpc_baratron', p)
    if logger.read_trigged():
        print p
        db_logger.enqueue_point_now('stm312_hpc_baratron', p)
        logger.clear_trigged()

