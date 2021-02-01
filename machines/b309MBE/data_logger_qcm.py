""" QCM logger, PVD309. Originally on rasppi106, but moved here due to repurposing of the rasppi."""
from __future__ import print_function
import threading
import time
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.intellemetrics_il800 as intellemetrics_il800
import PyExpLabSys.drivers.inficon_sqm160 as inficon_sqm160
from PyExpLabSys.common.utilities import get_logger
import credentials

LOGGER = get_logger('PVD309 QCM', level='info', file_log=True,
                    file_name='qcm_log.txt', terminal_log=True)

class QcmReader(threading.Thread):
    """ QCM Reader """
    def __init__(self, qcm):
        threading.Thread.__init__(self)
        self.qcm = qcm
        self.rate = None
        self.thickness = None
        self.frequency = None
        self.quit = False
        self.ttl = 20

    def value(self, channel):
        """ Read values """
        self.ttl = self.ttl - 1
        if self.ttl < 0:
            self.quit = True
            return_val = None
        else:
            if channel == 0:
                return_val = self.rate
            if channel == 1:
                return_val = self.thickness
            if channel == 2:
                return_val = self.frequency
        return return_val

    def run(self):
        while not self.quit:
            self.ttl = 50
            time.sleep(0.1)
            self.thickness = self.qcm.thickness()
            self.frequency = self.qcm.frequency()
            self.rate = self.qcm.rate()

def main():
    """ Main loop """
    il800 = intellemetrics_il800.IL800('/dev/serial/by-id/' +
                                       'usb-Prolific_Technology_Inc.' +
                                       '_USB-Serial_Controller_D-if00-port0')
    sqm160 = inficon_sqm160.InficonSQM160('/dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0')

    qcm1 = QcmReader(il800)
    qcm1.start()

    qcm2 = QcmReader(sqm160)
    qcm2.start()

    time.sleep(2.5)

    codenames = ['pvd309_qcm1_rate', 'pvd309_qcm1_thickness', 'pvd309_qcm1_frequency',
                 'pvd309_qcm2_rate', 'pvd309_qcm2_thickness', 'pvd309_qcm2_frequency']

    loggers = {}
    loggers[codenames[0]] = ValueLogger(qcm1, comp_val=0.01,
                                        comp_type='lin', channel=0)
    loggers[codenames[1]] = ValueLogger(qcm1, comp_val=0.1,
                                        comp_type='lin', channel=1)
    loggers[codenames[2]] = ValueLogger(qcm1, comp_val=1,
                                        comp_type='lin', channel=2)
    loggers[codenames[3]] = ValueLogger(qcm2, comp_val=0.3,
                                        comp_type='lin', channel=0)
    loggers[codenames[4]] = ValueLogger(qcm2, comp_val=0.1,
                                        comp_type='lin', channel=1)
    loggers[codenames[5]] = ValueLogger(qcm2, comp_val=1,
                                        comp_type='lin', channel=2)
    for name in codenames:
        loggers[name].daemon = True
        loggers[name].start()


    livesocket = LiveSocket('pvd309 qcm logger', codenames)
    livesocket.start()

    socket = DateDataPullSocket('pvd309 qcm', codenames, timeouts=[1.0]*len(codenames))
    socket.start()

    db_logger = ContinuousLogger(table='dateplots_pvd309',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=codenames)
    db_logger.start()

    while qcm1.isAlive() and qcm2.isAlive():
        time.sleep(0.25)
        for name in codenames:
            value = loggers[name].read_value()
            livesocket.set_point_now(name, value)
            socket.set_point_now(name, value)
            if loggers[name].read_trigged():
                print(name + ': ' + str(value))
                db_logger.enqueue_point_now(name, value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        LOGGER.exception(e)
        raise e
