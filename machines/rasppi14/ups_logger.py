# pylint: disable= R0904, C0103

import threading
import logging
import time
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
import PyExpLabSys.drivers.galaxy_3500 as galaxy_3500
import credentials

class UpsReader(threading.Thread):
    """ Run the ups-instance and keep status updated """
    def __init__(self, ups):
        threading.Thread.__init__(self)
        self.ups = ups
        self.status = ups.status
        self.ttl = 100
        self.quit = False

    def value(self, channel):
        """ Return the value of the reader """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        value_params = ['Internal Temperature', 'Output kVA L1',
                        'Output kVA L2', 'Output kVA L3',
                        'Output Current L1', 'Output Current L2',
                        'Output Current L3', 'Input Frequency',
                        'Input Voltage L1', 'Input Voltage L2',
                        'Input Voltage L3', 'Output Voltage L1',
                        'Output Voltage L2', 'Output Voltage L3',
                        'Battery Voltage', 'Battery Current',
                        'Battery State Of Charge', 'Output Frequency']
        return_val = self.status[value_params[channel]]
        return return_val

    def run(self):
        while not self.quit:
            print self.ttl
            self.ups.alarms()
            self.ups.battery_charge()
            self.ups.output_measurements()
            self.ups.input_measurements()
            self.ups.battery_status()
            self.ups.temperature()
            self.status = self.ups.status
            self.ttl = 100
            time.sleep(1)

logging.basicConfig(filename="logger.txt", level=logging.ERROR)
logging.basicConfig(level=logging.ERROR)

UPS = galaxy_3500.Galaxy3500('b312-ups')
Reader = UpsReader(UPS)
Reader.daemon = True
Reader.start()

time.sleep(5)

codenames = ['b312_ups_temperature', 'b312_ups_kVAPh1', 'b312_ups_kVAPh2',
             'b312_ups_kVAPh3', 'b312_ups_output_current_Ph1',
             'b312_ups_output_current_Ph2', 'b312_ups_output_current_Ph3',
             'b312_ups_input_frequency', 'b312_ups_input_voltage_Ph1',
             'b312_ups_input_voltage_Ph2', 'b312_ups_input_voltage_Ph3',
             'b312_ups_output_voltage_Ph1', 'b312_ups_output_voltage_Ph2',
             'b312_ups_output_voltage_Ph3', 'b312_ups_battery_voltage',
             'b312_ups_battery_current', 'b312_ups_battery_state_of_charge',
             'b312_ups_output_frequency']

loggers = {}
for i in range(0, len(codenames)):
    loggers[codenames[i]] = ValueLogger(Reader, comp_val=0.1, channel=i)
    loggers[codenames[i]].start()
socket = DateDataPullSocket('UPS status', codenames,
                            timeouts=[5.0] * len(codenames))
socket.start()

live_socket = LiveSocket('UPS Status', codenames, 2)
live_socket.start()

db_logger = ContinuousLogger(table='dateplots_ups_b312',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=codenames)
db_logger.start()

time.sleep(5)

while Reader.isAlive():
    time.sleep(0.25)
    for name in codenames:
        v = loggers[name].read_value()
        #print 'V: ' + str(v)
        socket.set_point_now(name, v)
        live_socket.set_point_now(name, v)
        if loggers[name].read_trigged():
            print v
            db_logger.enqueue_point_now(name, v)
            loggers[name].clear_trigged()

