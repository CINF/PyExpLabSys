"""This script monotors the Vortex gas alarm system in building 307
and logs the output
"""

import time

import credentials
from PyExpLabSys.drivers.crowcon import Vortex
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.utilities import get_logger
LOGGER = get_logger('b307gasalarm', file_log=True)


def identity_to_codename(identity):
    """Convert the identity the sensor returns to the codename used in the
    database
    """
    identity = identity.replace(' ', '_').replace('/', '-')
    return 'B307_gasalarm_{}'.format(identity)


def main(db_logger, vortex):
    """Main monitoring and logging loop"""
    detector_numbers = range(1, vortex.get_number_installed_detectors() + 1)
    detector_info = {detector_num: vortex.detector_configuration(detector_num)
                     for detector_num in detector_numbers}
    # trip_levels are the differences that are required to force a log
    # The levels are set to 2 * the communication resolution
    # (1000 values / full range)
    trip_levels = {detector_num: info.range * 2.0 / 1000.0
                   for detector_num, info in detector_info.items()}
    # Initiate last measured values and their corresponding times
    last_values = {detector_num: - (10 ** 9) for detector_num in detector_numbers}
    last_times = {detector_num: 0 for detector_num in detector_numbers}

    # Continuous logging loop
    while True:
        for detector_num in detector_numbers:
            # Get detector info and levels for this detector
            conf = detector_info[detector_num]
            levels = vortex.get_detector_levels(detector_num)

            now = time.time()
            time_condition = now - last_times[detector_num] >= 600
            value_condition = abs(last_values[detector_num] - levels.level)\
                > trip_levels[detector_num]
            if time_condition or value_condition:
                db_logger.enqueue_point(identity_to_codename(conf.identity),
                                        now, levels.level)
                # Update last values
                last_values[detector_num] = levels.level
                last_times[detector_num] = now


if __name__ == '__main__':
    # Start logger
    CODENAMES = ['B307_gasalarm_CO_051', 'B307_gasalarm_H2_051',
                 'B307_gasalarm_CO_055', 'B307_gasalarm_H2_055',
                 'B307_gasalarm_CO_059', 'B307_gasalarm_H2_059',
                 'B307_gasalarm_CO_061', 'B307_gasalarm_H2_061',
                 'B307_gasalarm_CO_42-43', 'B307_gasalarm_H2_2sal',
                 'B307_gasalarm_CO_932', 'B307_gasalarm_H2_932']
    DB_LOGGER = ContinuousLogger(table='dateplots_b307gasalarm',
                                 username=credentials.USERNAME,
                                 password=credentials.PASSWORD,
                                 measurement_codenames=CODENAMES)
    DB_LOGGER.start()

    # Start driver
    VORTEX = Vortex('/dev/ttyUSB0', 1)
    LOGGER.info('Vortex driver opened')

    try:
        main(DB_LOGGER, VORTEX)
    except KeyboardInterrupt:
        DB_LOGGER.stop()
        VORTEX.close()
    time.sleep(2)

