# pylint: disable=C0301,R0904, C0103
import threading
import logging
import time
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.value_logger import LoggingCriteriumChecker
from PyExpLabSys.common.sockets import DateDataPullSocket
import PyExpLabSys.drivers.omega_cni as omega_cni
import PyExpLabSys.drivers.NGC2D as NGC2D
import credentials

class Reader(threading.Thread):
    def __init__(self, iongauge, omega, codenames, pullsocket):
        threading.Thread.__init__(self)
        self.iongauge = iongauge
        self.omega = omega
        self.codenames = codenames
        self.pullsocket = pullsocket
        self.values = dict()
        for codename in codenames:
            self.values[codename] = None
        self.quit = False

    def run(self):
        """Main thread activity"""
        while not self.quit:
            # Pressure
            pressure = float(self.iongauge.ReadPressure())
            if pressure == -1:
                print('Pressure gauge off - log as atmosphere')
                pressure = 1000
            self.values[self.codenames[0]] = pressure
            self.pullsocket.set_point_now(self.codenames[0], pressure)

            # Temperature
            temperature = self.omega.read_temperature()
            self.values[self.codenames[1]] = temperature
            self.pullsocket.set_point_now(self.codenames[1], temperature)
            time.sleep(0.2)
        else:
            self.pullsocket.stop()

    def stop(self,):
        self.quit = True

if __name__ == '__main__':
    # Drivers
    omega_port = '/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTZ6JV6C-if00-port0'
    ngc2d_port = '/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
    iongauge = NGC2D.NGC2D_comm(device=ngc2d_port)
    omega = omega_cni.ISeries(omega_port, 9600, comm_stnd='rs232')

    # Codenames
    codenames = ['omicron_nanobeam_pressure',
                 'omicron_nanobeam_temperature']
    pullsocket = DateDataPullSocket('nanobeam_state', codenames, timeouts=4, port=9000)
    reader = Reader(iongauge, omega, codenames, pullsocket)
    reader.daemon = True
    reader.start()
    print('Codenames used: {}'.format(codenames))

    # Criterium checker
    criterium_checker = LoggingCriteriumChecker(
        codenames=codenames,
        types=['log', 'lin'],
        criteria=[0.15, 0.5],
        time_outs=[600, 600],
        )

    db_logger = ContinuousDataSaver(
        'dateplots_omicron',
        credentials.user,
        credentials.passwd,
        codenames)
    db_logger.daemon = True
    db_logger.start()
    print('Starting database logger')
    time.sleep(1)

    run = True
    t0 = time.time()
    while run:
        try:
            time.sleep(1)
            for codename in codenames:
                value = reader.values[codename]
                if value is None:
                    print('NONE encountered - check equiptment!')
                else:
                    if criterium_checker.check(codename, value):
                        print(codename, value, (time.time() - t0)/60.)
                        db_logger.save_point_now(codename, value)
        except:
            print('Stopping everything:')
            run = False
            reader.stop()
            db_logger.stop()
            print('Everything is stopped!')
            raise
