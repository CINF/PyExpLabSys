""" Pressure and temperature logger """
from __future__ import print_function
import threading
import time
from PyExpLabSys.common.database_saver import ContinuousDataSaver
### <TMP ###
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn
### TMP> ###
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.xgs600 as xgs600
import PyExpLabSys.drivers.agilent_34972A as agilent_34972A
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

# Set to False to not save pressure in xy_table high res
SAVE_PRESSURE = False
SAVE_HOURS = 48

class MuxReader(threading.Thread):
    """ Analog reader """
    def __init__(self, mux):
        threading.Thread.__init__(self)
        self.mux = mux
        self.ttl = 20
        self.temperature = None
        self.quit = False

    def value(self):
        """ Read the temperaure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        return self.temperature

    def run(self):
        while not self.quit:
            self.ttl = 20
            time.sleep(1)
            mux_list = self.mux.read_single_scan()
            self.temperature = mux_list[0]

class PressureReader(threading.Thread):
    """ Pressure reader """
    def __init__(self, xgs):
        threading.Thread.__init__(self)
        self.xgs = xgs
        self.pressure = None
        self.rough = None
        self.quit = False
        self.ttl = 20

    def value(self, channel=0):
        """ Read the pressure """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
        if channel == 0:
            return self.pressure
        elif channel == 1:
            return self.rough

    def run(self):
        while not self.quit:
            self.ttl = 20
            time.sleep(0.5)
            press = self.xgs.read_all_pressures()
            try:
                self.pressure = press[0]
            except IndexError:
                print("av")
                self.pressure = 0
            try:
                self.rough = press[1]
            except IndexError:
                print("Rough read error")
                self.rough = 0

def main():
    """ Main code """
    #mux_instance = agilent_34972A.Agilent34972ADriver(interface='lan', hostname='volvo-agilent-34972a')
    port = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'
    xgs_instance = xgs600.XGS600Driver(port)

    #analog_measurement = MuxReader(mux_instance)
    #analog_measurement.start()

    pressure = PressureReader(xgs_instance)
    print('-')
    pressure.start()

    time.sleep(2.5)

    #codenames = ['volvo_pressure', 'volvo_temperature']
    codenames = ['volvo_pressure', 'volvo_rough_pressure']
    loggers = {}
    loggers[codenames[0]] = ValueLogger(pressure, comp_val=0.1, comp_type='log', low_comp=1e-9, channel=0)
    loggers[codenames[0]].start()
    loggers[codenames[1]] = ValueLogger(pressure, comp_val=0.1, comp_type='log', low_comp=1e-11, channel=1)
    loggers[codenames[1]].start()
    #loggers[codenames[2]] = ValueLogger(analog_measurement, comp_val=0.5, comp_type='lin')
    #loggers[codenames[2]].start()

    socket = DateDataPullSocket('Volvo data logger', codenames, timeouts=1.0)
    socket.start()

    livesocket = LiveSocket('Volvo data logger', codenames)
    livesocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_volvo',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    ### <TMP ###
    if SAVE_PRESSURE:
        tmp_logger = DataSetSaver(
            'measurements_dummy',
            'xy_values_dummy',
            credentials.dummyuser,
            credentials.dummypasswd,
        )
        tmp_logger.start()

        time.sleep(2)

        t0 = time.time()
        meta_data = {
            "Time": CustomColumn(t0, "FROM_UNIXTIME(%s)"),
            "comment": 'Main chamber pressure during depositions',
            "type": 71, # 12 or 71 for pressure
            "sem_voltage": -1,
            "preamp_range": -1,
        }
        tmp_logger.add_measurement("pressure", meta_data)
        #time.sleep(2)
    ### TMP> ###

    #while pressure.isAlive() and analog_measurement.isAlive():
    old_pressure = -1
    last_save = 0
    while True:
        time.sleep(0.25)
        for name in codenames:
            value = loggers[name].read_value()
            socket.set_point_now(name, value)
            livesocket.set_point_now(name, value)
            ### <TMP ###
            if name == 'volvo_pressure' and SAVE_PRESSURE:
                t_now = time.time() - t0
                if value != old_pressure or t_now - last_save > 5:
                    if t_now < SAVE_HOURS * 3600:
                        print(t_now, value)
                        tmp_logger.save_point('pressure', (t_now, value))
                        old_pressure = value
                        last_save = t_now
            ### TMP> ###
            if loggers[name].read_trigged():
                print(value)
                db_logger.save_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    while True:
        try:
            main()
        except KeyboardInterrupt:
            break
        except OSError as exception:
            print("Got '{}'. Waiting 5 min and run again".format(exception))
            time.sleep(300)

