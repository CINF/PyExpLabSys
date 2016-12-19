# pylint: disable=C0103
"""This file logs data from the chiller at the thetaprobe"""
import time
import math
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.chiller_reader import ChillerReader
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)


LOG = get_logger('chiller_logger_thetaprobe')


def main():
    """Main function"""
    chiller_port = '/dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0'
    LOG.info('Using chiller port %s', chiller_port)
    reader = ChillerReader(chiller_port)
    reader.start()
    LOG.info('ChillerReader started')

    codenames = ['thetaprobe_chiller_temperature',
                 'thetaprobe_chiller_flow',
                 'thetaprobe_chiller_temperature_ambient',
                 'thetaprobe_chiller_pressure',
                 'thetaprobe_chiller_temperature_setpoint']
    LOG.debug('Using codenames %s', codenames)
    loggers = {}
    for i in range(0, len(codenames)):
        loggers[codenames[i]] = ValueLogger(reader, comp_val=0.1, channel=i)
        loggers[codenames[i]].start()

    live_socket_name = 'Thetaprobe chiller'
    live_socket = LiveSocket(live_socket_name, codenames)
    live_socket.start()
    LOG.info('Live socket init and started with name "%s"', live_socket_name)

    db_table = 'dateplots_thetaprobe'
    db_logger = ContinuousDataSaver(continuous_data_table=db_table,
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()
    LOG.info('ContinuousLogger init and started on table "%s"', db_table)

    time.sleep(5)

    while reader.isAlive():
        time.sleep(0.25)
        for name in codenames:
            value = loggers[name].read_value()
            if not math.isnan(value):
                live_socket.set_point_now(name, value)
                if loggers[name].read_trigged():
                    LOG.debug('Log value %s for codename "%s"', value, name)
                    db_logger.save_point_now(name, value)
                    loggers[name].clear_trigged()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        LOG.exception()
        raise
