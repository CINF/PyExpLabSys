""" App to log output from Pfeiffer Turbo Pumps """
# -*- coding: utf-8 -*-
import time
import sys
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import LiveSocket
import PyExpLabSys.drivers.pfeiffer_turbo_pump as tp
from PyExpLabSys.common.utilities import get_logger

sys.path.append('/home/pi/PyExpLabSys/machines/' + sys.argv[1])
import settings # pylint: disable=F0401

LOGGER = get_logger('Turbo Pump', level='info', file_log=True,
                    file_name='turbo_log.txt', terminal_log=False)

def main():
    """ Main loop """
    mainpump = tp.TurboDriver(adress=1, port=settings.port)
    mainpump.start()

    tui = tp.CursesTui(mainpump)
    tui.daemon = True
    tui.start()

    reader = tp.TurboReader(mainpump)
    reader.daemon = True
    reader.start()

    time.sleep(10) # Allow reader to make meaningfull moving avarage

    codenames = [settings.table_prefix + '_turbo_speed',
                 settings.table_prefix + '_turbo_power',
                 settings.table_prefix + '_turbo_current',
                 settings.table_prefix + '_turbo_temp_motor',
                 settings.table_prefix + '_turbo_temp_bottom',
                 settings.table_prefix + '_turbo_temp_bearings',
                 settings.table_prefix + '_turbo_temp_electronics']
    loggers = {}

    loggers[codenames[0]] = tp.TurboLogger(reader, 'rotation_speed', maximumtime=600)
    loggers[codenames[1]] = tp.TurboLogger(reader, 'drive_power', maximumtime=600)
    loggers[codenames[2]] = tp.TurboLogger(reader, 'drive_current', maximumtime=600)
    loggers[codenames[3]] = tp.TurboLogger(reader, 'temp_motor', maximumtime=600)
    loggers[codenames[4]] = tp.TurboLogger(reader, 'temp_bottom', maximumtime=600)
    loggers[codenames[5]] = tp.TurboLogger(reader, 'temp_bearings', maximumtime=600)
    loggers[codenames[6]] = tp.TurboLogger(reader, 'temp_electronics', maximumtime=600)

    for name in codenames:
        loggers[name].daemon = True
        loggers[name].start()

    livesocket = LiveSocket(settings.name + '-turboreader', codenames, 2)
    livesocket.start()

    socket = DateDataPullSocket(settings.name + '-turboreader', codenames,
                                timeouts=[1.0] * len(codenames), port=9000)
    socket.start()

    db_logger = ContinuousLogger(table=settings.table,
                                 username=settings.user,
                                 password=settings.passwd,
                                 measurement_codenames=codenames)
    db_logger.start()
    time.sleep(5)

    while mainpump.running:
        time.sleep(0.1)
        for name in codenames:
            value = loggers[name].read_value()
            socket.set_point_now(name, value) # Notice, this is the averaged value
            livesocket.set_point_now(name, value) # Notice, this is the averaged value
            if loggers[name].trigged:
                db_logger.enqueue_point_now(name, value)
                loggers[name].trigged = False

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        LOGGER.exception(e)
        raise(e)
