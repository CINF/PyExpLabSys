"""This script monitors the Vortex gas alarm system in building 312
and logs the output

For the status logs:
 * Numbers 101-112 are detectors (1-12)
 * 120 is the system status
 * 121 is the system power status
"""

import time
import json
import sys

import credentials
from PyExpLabSys.drivers.crowcon import Vortex
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.utilities import get_logger
LOGGER = get_logger('b312gasalarm', level='debug')
import MySQLdb

# Python 3 check
if sys.version_info.major < 3:
    raise RuntimeError('Run with Python 3')

# Gas alarm configuration to codename translation.
# NOTE key is: '{conf.number} {conf.identity} {conf.unit}'.format(conf=conf)
CONF_TO_NAME = {
    '1 MikroLab PPM': 'B312_gasalarm_H2S_microscopy_west',
    '2 Hal PPM': 'B312_gasalarm_H2S_hall_west',
    '3 KemiLab PPM': 'B312_gasalarm_H2S_chemlab',
}

# device numbers for status table
NUMBER_OF_DETECTORS_IN_USE = 3
SYSTEM_STATUS_DEVICE = 120
POWER_STATUS_DEVICE = 121
DETECTOR_NUM_TO_DEVICE_NUM = {n: n + 100 for n in range(1, NUMBER_OF_DETECTORS_IN_USE + 1)}


# pylint: disable=R0902
class GasAlarmMonitor(object):
    """Class that monitors the gas alarm the building 312"""

    def __init__(self):
        # Start logger
        codenames = list(CONF_TO_NAME.values())
        self.db_saver = ContinuousDataSaver(
            continuous_data_table='dateplots_b312gasalarm',
            username=credentials.USERNAME,
            password=credentials.PASSWORD,
            measurement_codenames=codenames,
        )
        self.db_saver.start()
        LOGGER.info('Logger started')

        # Init live socket
        self.live_socket = LiveSocket(name='gas_alarm_312_live', codenames=codenames,
                                      internal_data_pull_socket_port=8001)
        self.live_socket.start()
        LOGGER.info('Live socket started')

        # Start driver
        self.vortex = Vortex('/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTY3G9FE-if00-port0', 2)
        LOGGER.info('Vortex driver opened')

        # Init database connection
        self.db_connection = MySQLdb.connect(
            host='servcinf-sql', user=credentials.USERNAME,
            passwd=credentials.PASSWORD, db='cinfdata',
        )
        self.db_cursor = self.db_connection.cursor()

        # Initiate static information. All information about the detectors except for the
        # list of their numbers are placed in dicts because the numbering starts at 1.
        # Detector numbers: [1, 2, 3, ..., 12]
        self.detector_numbers = list(range(1, NUMBER_OF_DETECTORS_IN_USE + 1))
        self.detector_info = {
            detector_num: self.vortex.detector_configuration(detector_num)
            for detector_num in self.detector_numbers
        }
        # trip_levels are the differences that are required to force a log
        # The levels are set to 2 * the communication resolution
        # (1000 values / full range)
        self.trip_levels = {detector_num: info.range * 2.0 / 1000.0 for
                            detector_num, info in self.detector_info.items()}

        # Initiate last measured values and their corresponding times
        self.detector_levels_last_values = \
            {detector_num: - (10 ** 9) for detector_num in self.detector_numbers}
        self.detector_levels_last_times = \
            {detector_num: 0 for detector_num in self.detector_numbers}
        self.detector_status_last_values = \
            {detector_num: {'inhibit': False, 'status': ['OK'],
                            'codename': self.detector_info[detector_num].identity}
             for detector_num in self.detector_numbers}
        self.detector_status_last_times = \
            {detector_num: 0 for detector_num in self.detector_numbers}

        # Initiate variables for system power status
        self.central_power_status_last_value = 'OK'
        self.central_power_status_last_time = - (10 ** 9)

        # Initiate variables for system status
        self.central_status_last_value = ['All OK']
        self.central_status_last_time = 0

    def close(self):
        """Close the logger and the connection to the Vortex"""
        self.db_saver.stop()
        LOGGER.info('Logger stopped')
        self.live_socket.stop()
        LOGGER.info('Live socket stopped')
        self.vortex.close()
        LOGGER.info('Vortex driver closed')

    @staticmethod
    def conf_to_codename(conf):
        """Convert the identity the sensor returns to the codename used in the
        database
        """
        conf = '{conf.number} {conf.identity} {conf.unit}'.format(conf=conf)
        return CONF_TO_NAME[conf]

    def main(self):
        """Main monitoring and logging loop"""
        # Each iteration takes about 5 sec
        while True:
            # Log detectors
            for detector_num in self.detector_numbers:
                self.log_detector(detector_num)

            # Log Vortex unit status (force log every 24 hours)
            self.log_central_unit()

    def log_detector(self, detector_num):
        """Get the levels from one detector and log if required"""
        # Get detector info and levels for this detector
        conf = self.detector_info[detector_num]
        codename = self.conf_to_codename(conf)
        LOGGER.debug('Use detector {} \'{}\''.format(detector_num, codename))
        levels = self.vortex.get_detector_levels(detector_num)
        LOGGER.debug('Levels read: {}'.format(levels))

        # Detector level
        now = time.time()
        # Always send to live socket
        self.live_socket.set_point_now(codename, levels.level)
        # Force log every 10 m
        time_condition = now - self.detector_levels_last_times[detector_num] > 600
        value_condition = abs(self.detector_levels_last_values[detector_num] - levels.level)\
                          >= self.trip_levels[detector_num]
        if time_condition or value_condition:
            LOGGER.debug('Send level to db trigged in time: {} or value: '
                         '{}'.format(time_condition, value_condition))
            self.db_saver.save_point(codename, (now, levels.level))
            # Update last values
            self.detector_levels_last_values[detector_num] = levels.level
            self.detector_levels_last_times[detector_num] = now
        else:
            LOGGER.debug('Level logging condition false')

        self.log_detector_status(detector_num, levels, conf)

    def log_detector_status(self, detector_num, levels, conf):
        """Sub function to log single detector status"""
        now = time.time()
        # Force log every 24 hours
        time_condition = now - self.detector_status_last_times[detector_num] > 86400
        codename = self.conf_to_codename(conf)
        status = {'inhibit': levels.inhibit, 'status': levels.status, 'codename': codename}
        value_condition = (status != self.detector_status_last_values[detector_num])

        # Check if we should log
        if time_condition or value_condition:
            check_in = time_condition and not value_condition
            LOGGER.info('Send detector status to db trigged on time: {} or '
                        'value: {}'.format(time_condition, value_condition))
            query = 'INSERT INTO status_b312gasalarm '\
                '(time, device, status, check_in) '\
                'VALUES (FROM_UNIXTIME(%s), %s, %s, %s);'
            values = (now, DETECTOR_NUM_TO_DEVICE_NUM[detector_num], json.dumps(status),
                      check_in)
            self._wake_mysql()
            self.db_cursor.execute(query, values)
            # Update last values
            self.detector_status_last_times[detector_num] = now
            self.detector_status_last_values[detector_num] = status
        else:
            LOGGER.debug('Detector status logging condition false')

    def log_central_unit(self):
        """Log the status of the central unit"""
        power_status = self.vortex.get_system_power_status().value
        now = time.time()
        # Force a log once per 24 hours
        time_condition = now - self.central_power_status_last_time > 86400
        value_condition = self.central_power_status_last_value != power_status
        LOGGER.debug('Read central power status: \'{}\''.format(power_status))
        if time_condition or value_condition:
            check_in = time_condition and not value_condition
            LOGGER.info('Send power status to db trigged in time: {} or '
                        'value: {}'.format(time_condition, value_condition))
            query = 'INSERT INTO status_b312gasalarm '\
                '(time, device, status, check_in) '\
                'VALUES (FROM_UNIXTIME(%s), %s, %s, %s);'
            values = (now, POWER_STATUS_DEVICE, json.dumps(power_status), check_in)
            self._wake_mysql()
            self.db_cursor.execute(query, values)
            # Update last values
            self.central_power_status_last_time = now
            self.central_power_status_last_value = power_status
        else:
            LOGGER.debug('Power status logging condition false')

        self.log_central_unit_generel()

    def log_central_unit_generel(self):
        """Log the generel status from the central"""
        generel_status = self.vortex.get_system_status()
        now = time.time()
        # Force a log once per 24 hours
        time_condition = now - self.central_status_last_time > 86400
        value_condition = generel_status != self.central_status_last_value
        LOGGER.debug(
            'Read central generel status: \'{}\''.format(generel_status))
        if time_condition or value_condition:
            check_in = time_condition and not value_condition
            LOGGER.info('Send central generel status to db trigged in time: {}'
                        ' or value: {}'.format(time_condition,
                                               value_condition))
            query = 'INSERT INTO status_b312gasalarm '\
                '(time, device, status, check_in) '\
                'VALUES (FROM_UNIXTIME(%s), %s, %s, %s);'
            values = (now, SYSTEM_STATUS_DEVICE, json.dumps(generel_status), check_in)
            self._wake_mysql()
            self.db_cursor.execute(query, values)
            # Update last values
            self.central_status_last_time = now
            self.central_status_last_value = generel_status
        else:
            LOGGER.debug('Central generel status logging confition false')

    def _wake_mysql(self):
        """Send a ping via the connection and re-initialize the cursor"""
        self.db_connection.ping(True)
        self.db_cursor = self.db_connection.cursor()


if __name__ == '__main__':
    # pylint: disable=C0103
    reset = True
    while True:
        try:
            if reset:
                gas_alarm_monitor = GasAlarmMonitor()
                time.sleep(1)
                reset = False
            gas_alarm_monitor.main()
        except KeyboardInterrupt:
            gas_alarm_monitor.close()
            break
        except (OSError, MySQLdb.OperationalError) as exception:
            # Any error caused by problems in power of network should go here
            LOGGER.warning("'{}' encoutered. Wait 5 min and reset.".format(exception))
            reset = True
        except Exception as exception:
            LOGGER.exception(exception)
            gas_alarm_monitor.close()
            raise exception

        if reset:
            # If we encounter the sort of problem that triggers a
            # reset, wait a little while
            time.sleep(300)

    time.sleep(2)
    LOGGER.info('Program has stopped')
