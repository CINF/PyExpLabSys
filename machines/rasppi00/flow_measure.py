""" measuring and logging of water flow for xps gun"""
# pylint: disable=C1001
import time
import wiringpi2 as wp
import sys
import threading
#sys.path.insert(1, '/home/pi/PyExpLabSys')
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.sockets import DataPushSocket

import credentials

name = 'stm312 xps water flow'
codenames = ['water_flow']
socket = DateDataPullSocket(name, codenames)

def setup_wiring():
    wp.wiringPiSetup()
    for i in range(0, 7):
        wp.pinMode(i, 0)

class ValueLogger(object):
    """ Read a continuously updated values and decides whether it is time to log a new point """
    def __init__(self, maximumtime=600,
                 comp_type='lin',
                 comp_val=1,
                 codename=None):
        self.maximumtime = maximumtime
        self.compare = {'type':comp_type, 'val':comp_val}
        self.codename = codename

        self.value = 0.0
        self.last = {'time':0.0, 'val':0.0}

        self.status = {'trigged':False}

    def add_logger(self, db_logger):
        """adding logger """
        self.db_logger = db_logger

    def trigger(self, value):
        """determins if the value should be logged"""
        self.value = value
        time_trigged = ((time.time() - self.last['time']) > self.maximumtime)
        if self.compare['type'] == 'lin':
            val_trigged = not (self.last['val'] - self.compare['val'] <
                               self.value <
                               self.last['val'] + self.compare['val'])
        elif self.compare['type'] == 'log':
            val_trigged = not (self.last['val'] * (1 - self.compare['val']) <
                               self.value <
                               self.last['val'] * (1 + self.compare['val']))
        if (time_trigged or val_trigged) and (self.value > 0):
            self.status['trigged'] = True
            self.last['time'] = time.time()
            self.last['val'] = self.value
            self.log_value()

    def log_value(self,):
        if self.status['trigged'] and self.codename != None:
            self.db_logger.enqueue_point_now(self.codename, self.value)
            self.status['trigged'] = False

class WaterFlow(threading.Thread):
    """measure the water flow"""
    def __init__(self,):
        threading.Thread.__init__(self)
        self.db_logger_avalible = False
        self._stop = False
        self.water_flow = 0.0
        self.codename = 'stm312_xray_waterflow'

    def add_valuelogger(self,):
        """adding connection to the value logger"""
        self.valuelogger = ValueLogger(maximumtime=600,
                                       comp_type='lin',
                                       comp_val=0.3,
                                       codename=self.codename)
        self.db_logger = ContinuousLogger(table='dateplots_stm312',
                                          username=credentials.user,
                                          password=credentials.passwd,
                                          measurement_codenames=[self.codename])
        self.db_logger.start()
        self.valuelogger.add_logger(self.db_logger)
        self.db_logger_avalible = True

    def run(self,):
        while not self._stop:
            now = wp.digitalRead(0)
            counter = 0
            counter_same = 0
            t0 = time.time()
            for i in range(0, 5000):
                new = wp.digitalRead(0)
                if now != new:
                    counter += 1
                    now = new
                else:
                    counter_same += 1
                time.sleep(0.0001)
            freq = 0.5 * counter / (time.time() - t0)
            self.water_flow = freq*60./6900
            print 'freq: ' + str(freq) + ' , integration time: ' + str(time.time() - t0) + ', L/min: ' + str(self.water_flow) + ', ident: ' + str(float(counter)/counter_same)
            socket.set_point_now('water_flow',self.water_flow)
            self.valuelogger.trigger(self.water_flow)

    def stop(self,):
        self._stop = True
        try:
            socket.stop()
        except:
            pass
        try:
            self.db_logger.stop()
            self.valuelogger.stop()
        except:
            pass

def main():
    """Main function to be executed"""
    setup_wiring()
    socket.deamon = True
    socket.start()
    waterflowclass = WaterFlow()
    waterflowclass.add_valuelogger()
    waterflowclass.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        waterflowclass.stop()

if __name__ == "__main__":
    main()
