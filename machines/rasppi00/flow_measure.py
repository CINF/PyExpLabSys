# pylint: disable=C0301, R0904, C0103

import sys
sys.path.insert(1, '/home/pi/PyExpLabSys')
import threading
import logging
import time
#from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
import wiringpi2 as wp
import credentials

class FlowReader(threading.Thread):
    """ Read Cooling water flow """
    def __init__(self,):
        threading.Thread.__init__(self)
        #self.adc = adc
        self.waterflow = 0.0
        self.quit = False
        wp.wiringPiSetup()
        for i in range(0, 7):
            wp.pinMode(i, 0)

    def value(self):
        """ Return the value of the reader """
        return self.waterflow

    def measure_bit_changes(self, maxtime=1.0):
        """Counts the bit flips corisponding to half sycle of the
        water wheel"""
        now = wp.digitalRead(0)
        counter = 0
        t0 = time.time()
        while maxtime > time.time()-t0:
            new = wp.digitalRead(0)
            if now != new:
                counter += 1
                now = new
            time.sleep(0.0001)
        freq = 0.5 * counter / (time.time() - t0)
        return freq

    def run(self):
        while not self.quit:
            time.sleep(0.2)
            freq = self.measure_bit_changes(0.7)
            self.waterflow = freq*60./6900


logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)


flowreader = FlowReader()
flowreader.daemon = True
flowreader.start()

logger = ValueLogger(flowreader, comp_val=0.1)
logger.start()

name = 'stm312_xray_waterflow'
codenames = ['stm312_xray_waterflow']
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
    flow = logger.read_value()
    socket.set_point_now(name, flow)
    live_socket.set_point_now(name, flow)
    if logger.read_trigged():
        print flow
        db_logger.enqueue_point_now(name, flow)
        logger.clear_trigged()

