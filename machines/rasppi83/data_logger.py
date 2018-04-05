""" Data logger for the mobile gas wall """
from __future__ import print_function
import threading
import logging
import time
import minimalmodbus
import serial
from PyExpLabSys.common.value_logger import ValueLogger, LoggingCriteriumChecker
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class TcReader(threading.Thread):
    """ Communicates with the Omega ?? """
    
    def __init__(self, port, datasocket, logger, db_logger):
        print('Initializing connection')
        self.comm = minimalmodbus.Instrument(port, 1)
        self.comm.serial.baudrate = 9600
        self.comm.serial.parity = serial.PARITY_EVEN
        self.comm.serial.timeout = 0.5
        error = 0
        while error < 10:
            try:
                self.temperature = self.comm.read_register(4096, 1, signed=True)
                break
            except OSError:
                error = error + 1
        if error > 9:
            exit('Error in communication with TC reader')
        print('Connection established')
        threading.Thread.__init__(self)
        self.quit = False
        self.datasocket = datasocket
        self.logger = logger
        self.db_logger = db_logger
        print('Module ready')

    def value(self):
        """ Return current value of reader """
        if (self.temperature < 1050) and (self.temperature > -300):
            return self.temperature

    def stop(self):
        """ Close thread properly """
        self.quit = True
        self.datasocket.stop()
        self.db_logger.stop()
        
    def run(self):
        time.sleep(5)
        error = 0
        lasttime = time.time()
        t0 = time.time()
        try:
            print('Entering while loop')
            while self.isAlive() and not self.quit:
                # Delay loop communication
                time.sleep(0.15)
                try:
                    self.temperature = self.comm.read_register(4096, 1, signed=True)
                    if error > 0:
                        error = 0
                    # Save points to sockets
                    self.datasocket.set_point_now(CODENAME, self.temperature)
                    if self.logger.check(CODENAME, self.temperature):
                        self.db_logger.save_point_now(CODENAME, self.temperature)
                        print(CODENAME + ': ' + str(self.temperature))
                    print(self.temperature, time.time()-t0, time.time()-lasttime)
                    lasttime = time.time()
                except:
                    error += 1
                    print('Error value: {}'.format(error))
                    if error > 9:
                        self.stop()
                        raise ValueError
        except KeyboardInterrupt:
            print('Force quit activated')
            self.stop()

CODENAME = 'omicron_tpd_temperature'
                
def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    #port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTY5BU0H-if00-port0'
    port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTY3GX3T-if00-port0'

    # Set up criterium logger
    logger = LoggingCriteriumChecker(
        codenames=[CODENAME],
        types=['lin'],
        criteria=[0.2],
        time_outs=[300],
        )

    # Set up pullsocket
    datasocket = DateDataPullSocket('mgw_temp', [CODENAME], timeouts=4, port=9000)
    datasocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_omicron',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=[CODENAME])
    db_logger.start()


    measurement = TcReader(port, datasocket, logger, db_logger)
    measurement.start()

                
if __name__ == '__main__':
    main()
