# -*- coding: utf-8 -*-
"""This script read the sample temperature from an Omega CNi3244_C24
temperature control unit and makes it available on a data socket. Furthermore,
it also log significant temperature points to the database.
"""
import time

from PyExpLabSys.drivers.omega import CNi3244_C24
from PyExpLabSys.common.sockets import DateDataPullSocket
#from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.utilities import get_logger


LOGGER = get_logger('temperatue', level='INFO', file_log=True,
                    file_name='temperature_log')
TEMPERATURE_CHANGE_THRESHOLD = 0.3
TIMEOUT = 600
SHORT_NAME = 'tts'
NAME = 'tower_temperature_sample'
FULL_NAME = 'Tower temperature of sample'


def main_measure_loop(cni, socket, db_logger):
    """The main measuring loop"""
    last_temp = -100000
    last_time = 0
    while True:
        # Current values
        now = time.time()
        current = cni.read_temperature()

        # The read_tempearture returns None if no thermocouple is connected
        if current is not None:
            # Set point on socket
            socket.set_point_now(SHORT_NAME, current)
    
            # Log if required
            if now - last_time > TIMEOUT or\
                    abs(current - last_temp) > TEMPERATURE_CHANGE_THRESHOLD:
                db_logger.save_point_now('tower_temperature_sample', current)                
                LOGGER.info('Value {} sent'.format(current))
                last_time = now
                last_temp = current


def main():
    LOGGER.info('main started')
    cni = CNi3244_C24(5)
    socket = DateDataPullSocket(FULL_NAME, [SHORT_NAME], timeouts=1.0)
    socket.start()
    db_logger = ContinuousDataSaver(
        continuous_data_table='dateplots_tower',
        username='tower',
        password='tower',
        measurement_codenames=[NAME],
    )
    db_logger.start()
    time.sleep(0.1)

    # Main part
    try:
        main_measure_loop(cni, socket, db_logger)
    except KeyboardInterrupt:
        LOGGER.info('Keyboard Interrupt. Shutting down!')
        db_logger.stop()
        cni.close()
        socket.stop()


if __name__ == '__main__':
    try:
        main()
    # This nasty little except on all exception makes sure that exception are
    # logged
    except Exception as e:
        LOGGER.exception(e)
        raise(e)
    raw_input("Press enter to exit")
