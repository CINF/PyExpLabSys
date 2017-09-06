# pylint: disable=C0103
"""This file logs data from the chiller at the thetaprobe"""
from __future__ import print_function
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

LOG = get_logger('chiller_logger_xrd')

def main():
    """Main function"""
    chiller_port = '/dev/serial/by-id/usb-1a86_USB2.0-Ser_-if00-port0'
    LOG.info('Using chiller port %s', chiller_port)

    new_chiller_port = '/dev/serial/by-id/'
    new_chiller_port += 'usb-Prolific_Technology_Inc._USB-Serial_Controller_D-if00-port0'
    LOG.info('Using chiller port %s', new_chiller_port)

    #Names without new-prefix refers to the old xrd, names including new
    #refers to the new xrd
    
    reader = ChillerReader(chiller_port)
    reader.start()
    LOG.info('ChillerReader started')

    new_reader = ChillerReader(new_chiller_port)
    new_reader.start()
    LOG.info('NewChillerReader started')

    codenames = ['xrd_chiller_temperature',
                 'xrd_chiller_flow',
                 'xrd_chiller_temperature_ambient',
                 'xrd_chiller_pressure',
                 'xrd_chiller_temperature_setpoint']

    new_codenames = ['new_xrd_chiller_temperature',
                     'new_xrd_chiller_flow',
                     'new_xrd_chiller_temperature_ambient',
                     'new_xrd_chiller_pressure',
                     'new_xrd_chiller_temperature_setpoint']
    LOG.debug('Using codenames %s', codenames)
    LOG.debug('Using codenames %s', new_codenames)
    
    loggers = {}
    for i in range(0, len(codenames)):
        loggers[codenames[i]] = ValueLogger(reader, comp_val=0.1, channel=i)
        loggers[codenames[i]].start()

    for i in range(0, len(new_codenames)):
        loggers[new_codenames[i]] = ValueLogger(new_reader, comp_val=0.1, channel=i)
        loggers[new_codenames[i]].start()

    live_socket_name = 'XRD chiller'
    live_socket = LiveSocket(live_socket_name, codenames + new_codenames)
    live_socket.start()
    LOG.info('Live socket init and started with name "%s"', live_socket_name)

    db_table = 'dateplots_xrd'
    db_logger = ContinuousDataSaver(continuous_data_table=db_table,
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()
    LOG.info('ContinuousLogger init and started on table "%s"', db_table)

    new_db_table = 'dateplots_new_xrd'
    new_db_logger = ContinuousDataSaver(continuous_data_table=new_db_table,
                                        username=credentials.new_user,
                                        password=credentials.new_passwd,
                                        measurement_codenames=new_codenames)
    new_db_logger.start()
    LOG.info('ContinuousLogger init and started on table "%s"', new_db_table)

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

        for name in new_codenames:
            value = loggers[name].read_value()
            if not math.isnan(value):
                live_socket.set_point_now(name, value)
                if loggers[name].read_trigged():
                    LOG.debug('Log value %s for codename "%s"', value, name)
                    new_db_logger.save_point_now(name, value)
                    loggers[name].clear_trigged()

if __name__ == '__main__':
    try:
        main()
    except Exception:
        LOG.exception()
        raise
