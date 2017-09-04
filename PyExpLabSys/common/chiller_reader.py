"""  Module for  monitoring a polyscience chiller """
from __future__ import print_function
import threading
import time
import PyExpLabSys.drivers.polyscience_4100 as polyscience_4100
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class ChillerReader(threading.Thread):
    """ Reader class that will monitor a polyscience chiller """
    def __init__(self, serial_port):
        threading.Thread.__init__(self)
        self.chiller = polyscience_4100.Polyscience4100(serial_port)
        self.status = {}
        self.status['temp'] = -9999
        self.status['flow'] = -9999
        self.status['temp_amb'] = -9999
        self.status['pressure'] = -9999
        self.status['setpoint'] = -9999
        self.status['running'] = 'Off'
        self.ttl = 100
        self.quit = False
        self.daemon = True

    def value(self, channel):
        """ Return the value of the reader """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        if channel == 0:
            return_val = self.status['temp']
        if channel == 1:
            return_val = self.status['flow']
        if channel == 2:
            return_val = self.status['temp_amb']
        if channel == 3:
            return_val = self.status['pressure']
        if channel == 4:
            return_val = self.status['setpoint']
        return return_val

    def run(self):
        while not self.quit:
            print(self.ttl)
            self.status['temp'] = self.chiller.read_temperature()
            self.status['flow'] = self.chiller.read_flow_rate()
            self.status['temp_amb'] = self.chiller.read_ambient_temperature()
            self.status['pressure'] = self.chiller.read_pressure()
            self.status['setpoint'] = self.chiller.read_setpoint()
            self.status['running'] = self.chiller.read_status()
            self.ttl = 100
            time.sleep(1)
