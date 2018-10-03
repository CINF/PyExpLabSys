# pylint: disable=no-member
""" Logger for nXDSni roughing pump """
from __future__ import print_function
import threading
import time
import sys
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
#from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.supported_versions import python2_and_3
from PyExpLabSys.drivers.edwards_nxds import EdwardsNxds
python2_and_3(__file__)
try:
    sys.path.append('/home/pi/PyExpLabSys/machines/' + sys.argv[1])
except IndexError:
    print('You need to give the name of the raspberry pi as an argument')
    print('This will ensure that the correct settings file will be used')
    exit()
import credentials # pylint: disable=wrong-import-position, import-error
import settings # pylint: disable=wrong-import-position, import-error

class PumpReader(threading.Thread):
    """ Read pump parameters """
    def __init__(self, port):
        threading.Thread.__init__(self)
        port = '/dev/serial/by-id/' + port
        self.pump = EdwardsNxds(port)
        self.values = {}
        self.values['temperature'] = -1
        self.values['controller_temperature'] = -1
        self.values['rotational_speed'] = -1
        self.values['run_hours'] = -1
        self.values['controller_run_hours'] = -1
        self.values['time_to_service'] = -1
        self.quit = False

    def value(self, channel):
        """ Return the value of the reader """
        value = self.values[channel]
        return value

    def run(self):
        print(self.values)
        time.sleep(1)
        while not self.quit:
            temperatures = self.pump.read_pump_temperature()
            controller_status = self.pump.pump_controller_status()
            self.values['temperature'] = temperatures['pump']
            self.values['controller_temperature'] = temperatures['controller']
            self.values['rotational_speed'] = self.pump.read_pump_status()['rotational_speed']
            self.values['run_hours'] = self.pump.read_run_hours()
            self.values['controller_run_hours'] = controller_status['controller_run_time']
            self.values['time_to_service'] = controller_status['time_to_service']

def main():
    """ Main function """
    pumpreaders = {}
    loggers = {}
    channels = ['temperature', 'controller_temperature', 'run_hours', 'rotational_speed',
                'controller_run_hours', 'time_to_service']
    codenames = []
    for port, codename in settings.channels.items():
        pumpreaders[port] = PumpReader(port)
        pumpreaders[port].daemon = True
        pumpreaders[port].start()
        pumpreaders[port].loggers = {}

        for channel in channels:
            codenames.append(codename + '_' + channel) # Build the list of codenames
            loggers[port + channel] = ValueLogger(pumpreaders[port], comp_val=0.9,
                                                  channel=channel, maximumtime=600)
            loggers[port + channel].start()

    #socket = DateDataPullSocket('Pump Reader', codenames, timeouts=2.0)
    #socket.start()
    #live_socket = LiveSocket('Pump Reader',  codenames)
    #live_socket.start()

    db_logger = ContinuousDataSaver(continuous_data_table=settings.table,
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames) # Codename list created
                                                                     # along with loggers
    db_logger.start()

    time.sleep(10)

    alive = True
    while alive:
        for port, base_codename in settings.channels.items():
            time.sleep(10)
            for channel in channels:
                if loggers[port + channel].is_alive is False:
                    alive = False

                codename = base_codename + '_' + channel
                value = loggers[port + channel].read_value()
                #socket.set_point_now(codename, value)
                #live_socket.set_point_now(codename, value)
                if loggers[port + channel].read_trigged():
                    print(port + channel + ': ' + str(value))
                    db_logger.save_point_now(codename, value)
                    loggers[port + channel].clear_trigged()

if __name__ == '__main__':
    while True:
        try:
            main()
        except KeyboardInterrupt:
            break
        except ValueError as exception:
            # May be caused by pumps going away
            time.sleep(300)
            print("Got '{}'. Wait 5 min and restart.".format(exception))
