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
    
    def __init__(self, port, datasocket, crit_logger=None, db_logger=None, codename='', output=False):
        super().__init__()
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
        #if self.temperature < -1000:
        #    self.temperature = None
        #threading.Thread.__init__(self)
        self.quit = False
        self.datasocket = datasocket
        self.logger = crit_logger
        self.db_logger = db_logger
        self.codename = codename
        print('Module ready')
        self.output = output

    def value(self):
        """ Return current value of reader """
        if (self.temperature < 1050) and (self.temperature > -300):
            return self.temperature

    def stop(self):
        """ Close thread properly """
        self.quit = True
        #self.datasocket.stop()
        if self.db_logger is not None:
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
                    if self.temperature < -250:
                        self.temperature = None
                    if error > 0:
                        error = 0
                    # Save points to sockets
                    self.datasocket.set_point_now(self.codename, self.temperature)
                    if self.logger is not None and self.db_logger is not None:
                        if self.logger.check(self.codename, self.temperature):
                            self.db_logger.save_point_now(self.codename, self.temperature)
                            print(self.codename + ': ' + str(self.temperature))
                    if self.output:
                        print(self.temperature, time.time()-t0, time.time()-lasttime)
                        lasttime = time.time()
                except:
                    error += 1
                    print('Error value: {}'.format(error))
                    if error > 9:
                        self.stop()
                        raise
        except KeyboardInterrupt:
            print('Force quit activated')
            self.stop()

CODENAMES = {'Sample': 'omicron_tpd_sample_temperature',
             'Base': 'omicron_tpd_temperature',
             }
                
def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    ports = dict()
    ports['Sample'] = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTY5BU0H-if00-port0'
    ports['Base'] =   '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTY3GX3T-if00-port0'

    # Set up criterium logger
    logger = LoggingCriteriumChecker(
        codenames=[CODENAMES['Base']],
        types=['lin'],
        criteria=[0.33],
        time_outs=[300],
        low_compare_values=[-200],
        )

    # Set up pullsocket
    datasocket = DateDataPullSocket('mgw_temp', list(CODENAMES.values()), timeouts=4, port=9000)
    datasocket.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_omicron',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=[CODENAMES['Base']])
    db_logger.start()


    measurement = TcReader(ports['Base'], datasocket, crit_logger=logger, db_logger=db_logger, codename=CODENAMES['Base'])
    measurement.start()

    sample_logger = TcReader(ports['Sample'], datasocket, codename=CODENAMES['Sample'])
    sample_logger.start()

    time.sleep(5)
    string = 'Base: {: <0 6.4} C, Sample: {: <0 6.4f} C'
    while True:
        try:
            time.sleep(1)
            print(string.format(measurement.temperature, sample_logger.temperature))
        except ValueError:
            print(repr(measurement.temperature))
            print(repr(sample_logger.temperature))
        except KeyboardInterrupt:
            measurement.stop()
            sample_logger.stop()
            time.sleep(2)
            print('\nTcReaders stopped')
            datasocket.stop()
            print('Pullsocket stopped\nExiting.')
            break
            
if __name__ == '__main__':
    main()
