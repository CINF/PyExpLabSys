# pylint: disable=no-member
""" Logger for roughing pumps """
import sys
import time
import socket
import pathlib
import threading

from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver

# from PyExpLabSys.common.sockets import DateDataPullSocket
# from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.drivers.edwards_nxds import EdwardsNxds
from PyExpLabSys.drivers.pfeiffer_hiscroll import PfeifferHiscroll

HOSTNAME = socket.gethostname()
machine_path = pathlib.Path.home() / 'machines' / HOSTNAME
sys.path.append(str(machine_path))

import credentials  # pylint: disable=wrong-import-position, import-error
import settings  # pylint: disable=wrong-import-position, import-error


class PumpReader(threading.Thread):
    """Read pump parameters"""

    def __init__(self, port, pump_type):
        threading.Thread.__init__(self)
        port = '/dev/serial/by-id/' + port
        if pump_type == 'nxds':
            self.pump = EdwardsNxds(port)
        elif pump_type == 'hiscroll':
            self.pump = PfeifferHiscroll(port, 2)
        else:
            print('Unknown pump type!')
            exit()

        self.values = {}
        self.values['pressure'] = -1
        self.values['temperature'] = -1
        self.values['controller_temperature'] = -1
        self.values['rotational_speed'] = -1
        self.values['run_hours'] = -1
        self.values['controller_run_hours'] = -1
        self.values['time_to_service'] = -1
        self.quit = False

    def value(self, channel):
        """Return the value of the reader"""
        value = self.values[channel]
        return value

    def run(self):
        print(self.values)
        time.sleep(1)
        while not self.quit:
            try:
                temperatures = self.pump.read_pump_temperature()
                controller_status = self.pump.pump_controller_status()
                self.values['temperature'] = temperatures['pump']
                self.values['controller_temperature'] = temperatures['controller']
                self.values['rotational_speed'] = self.pump.rotational_speed()['actual']
                self.values['run_hours'] = self.pump.read_run_hours()
                self.values['controller_run_hours'] = controller_status[
                    'controller_run_time'
                ]
                self.values['time_to_service'] = controller_status['time_to_service']
                self.values['pressure'] = self.pump.pressure()

            except OSError:
                print('Error reading from pump')
                time.sleep(2)
                self.values['pressure'] = -1
                self.values['temperature'] = -1
                self.values['controller_temperature'] = -1
                self.values['rotational_speed'] = -1
                self.values['run_hours'] = -1
                self.values['controller_run_hours'] = -1
                self.values['time_to_service'] = -1


def main():
    """Main function"""
    pumpreaders = {}
    loggers = {}
    channels = [
        'temperature',
        'controller_temperature',
        'run_hours',
        'rotational_speed',
        'controller_run_hours',
        'time_to_service',
        'pressure',
    ]
    codenames = []
    # for port, codename in settings.channels.items():
    for port, info in settings.channels.items():
        codename = info[0]
        pump_type = info[1]
        pumpreaders[port] = PumpReader(port, pump_type)
        pumpreaders[port].daemon = True
        pumpreaders[port].start()
        pumpreaders[port].loggers = {}

        for channel in channels:
            codenames.append(codename + '_' + channel)  # Build the list of codenames
            loggers[port + channel] = ValueLogger(
                pumpreaders[port], comp_val=1.1, channel=channel, maximumtime=600
            )
            loggers[port + channel].start()

    # socket = DateDataPullSocket('Pump Reader', codenames, timeouts=2.0)
    # socket.start()
    # live_socket = LiveSocket('Pump Reader',  codenames)
    # live_socket.start()

    db_logger = ContinuousDataSaver(
        continuous_data_table=settings.table,
        username=credentials.user,
        password=credentials.passwd,
        measurement_codenames=codenames,
    )
    db_logger.start()

    time.sleep(10)

    alive = True
    while alive:
        for port, info in settings.channels.items():
            base_codename = info[0]
            time.sleep(10)
            for channel in channels:
                if loggers[port + channel].is_alive is False:
                    alive = False

                codename = base_codename + '_' + channel
                value = loggers[port + channel].read_value()
                # socket.set_point_now(codename, value)
                # live_socket.set_point_now(codename, value)
                if loggers[port + channel].read_trigged():
                    print(port + ' ' + channel + ': ' + str(value))
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
