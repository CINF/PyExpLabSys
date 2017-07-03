""" Pressure and temperature logger """
from __future__ import print_function
import threading
import time
import logging
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.value_logger import ValueLogger
import PyExpLabSys.drivers.mks_925_pirani as mks_925_pirani
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class Reader(threading.Thread):
    """ Temperature reader """
    def __init__(self, gauges):
        threading.Thread.__init__(self)
        self.gauges = gauges
        self.ttl = 20
        self.pressure = {}
        self.quit = False

    def value(self, channel):
        """ Read the temperaure """
        self.ttl = self.ttl - 1
        if channel == 0:
            value = self.pressure['old']
        if channel == 1:
            value = self.pressure['ng']
        if self.ttl < 0:
            self.quit = True
            value = None
        return value

    def run(self):
        while not self.quit:
            self.ttl = 20
            for key in ['old', 'ng']:
                self.pressure[key] = self.gauges[key].read_pressure()
            time.sleep(0.1)

def main():
    """ Main function """
    logging.basicConfig(filename="logger.txt", level=logging.ERROR)
    logging.basicConfig(level=logging.ERROR)

    ports = ['/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTWRZWVS-if00-port0',
             '/dev/serial/by-id/usb-FTDI_USB-RS232_Cable_FTWXB4EW-if00-port0']

    mks_list = {}
    for i in range(0, 2):
        _mks = mks_925_pirani.Mks925(ports[i])
        name = ''
        error = 0
        while len(name) < 5:
            name = _mks.read_serial()
            name = name.strip()
            error = error + 1
            if error > 10:
                print('No unit connected to ' + ports[i])
                break
        if name == '1107638964':
            mks_list['ng'] = mks_925_pirani.Mks925(ports[i])
            mks_list['ng'].change_unit('MBAR')
            print('Pirani, ng buffer:' + ports[i] + ', serial:' + name)
        elif name == '1027033634':
            mks_list['old'] = mks_925_pirani.Mks925(ports[i])
            mks_list['old'].change_unit('MBAR')
            print('Pirani, old buffer:'+ ports[i] + ', serial:' + name)
        else:
            print('Pirani, Unknown:'+ ports[i] + ', serial:' + name)
            print(_mks.read_serial())

    if len(mks_list) == 2:
        measurement = Reader(mks_list)
        measurement.start()

        time.sleep(2.5)

        codenames = ['mr_buffer_pressure', 'microreactorng_pressure_buffer']

        try:
            name = chr(0x03BC) # Python 3
        except ValueError:
            name = unichr(0x03BC) # Python 2
        loggers = {}

        for i in range(len(codenames)):
            loggers[codenames[i]] = ValueLogger(measurement, comp_val=0.1,
                                                low_comp=1e-4, comp_type='log',
                                                channel=i)
            loggers[codenames[i]].start()


        socket = DateDataPullSocket(name + '-reactor NG temperature',
                                    codenames, timeouts=[1.0, 1.0])
        socket.start()

        livesocket = LiveSocket(name + '-reactors pressures',
                                codenames)
        livesocket.start()

        db_logger = {}
        db_logger[codenames[0]] = ContinuousDataSaver(continuous_data_table=
                                                      'dateplots_microreactor',
                                                      username=credentials.user_old,
                                                      password=credentials.passwd_old,
                                                      measurement_codenames=codenames)

        db_logger[codenames[1]] = ContinuousDataSaver(continuous_data_table=
                                                      'dateplots_microreactorNG',
                                                      username=credentials.user_new,
                                                      password=credentials.passwd_new,
                                                      measurement_codenames=codenames)
        db_logger[codenames[0]].start()
        db_logger[codenames[1]].start()

        while measurement.isAlive():
            time.sleep(0.25)
            for name in codenames:
                value = loggers[name].read_value()
                socket.set_point_now(name, value)
                livesocket.set_point_now(name, value)
                if loggers[name].read_trigged():
                    print("Codename: {}".format(name))
                    print("Value: {}".format(value))
                    print('---')
                    db_logger[name].save_point_now(name, value)
                    loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
