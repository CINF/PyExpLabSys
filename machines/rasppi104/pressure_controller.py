""" Pressure xgs600 controller for microreactors """
from __future__ import print_function
import time
import threading
import socket
import pickle
import PyExpLabSys.drivers.xgs600 as xgs600
#import PyExpLabSys.common.
from pressure_controller_xgs600 import xgs600Control# This is my idea so far!
import PyExpLabSys.common.utilities
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.utilities import activate_library_logging
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.supported_versions import python2_and_3
PyExpLabSys.common.utilities.ERROR_EMAIL = 'alexkbb@fysik.dtu.dk'
python2_and_3(__file__)
import credentials


try:
    MICRO = chr(0x03BC) # Python 3
except ValueError:
    MICRO = unichr(0x03BC) # Python 2

#### UPDATE  PRESSURE CONTROL LOGGING ####

#LOGGER = get_logger(MICRO + '-reactorNG Temperature control', level='ERROR', file_log=True,
#                    file_name='temp_control.log', terminal_log=False, email_on_warnings=False)
#activate_library_logging('PyExpLabSys.common.microreactor_temperature_control',
#                         logger_to_inherit_from=LOGGER)
#activate_library_logging('PyExpLabSys.auxiliary.pid', logger_to_inherit_from=LOGGER)

#LOGGER.warn('Program started')

def main():
    """ Main function """
    port = '/dev/ttyUSB0'#.usbserial-FTDFVMFT' # 'usb-Prolific_Technology_Inc._USB-Serial_Controller-if00-port0'
    codenames = ['pressure', 'state']
    socket_name = MICRO + '-reactorANH_xgs600_pressure_control'
    setpoint_channel_userlabel_on_off = {'T1': [1, 'NGBUF', '1.333E-04', '2.000E+00'],'T2': [2, 'IGMC', '1.000E-11', '1.000E-05'], 'T3': [3, 'NGBUF', '1.333E-04', '1.000E+00']}
    devices = ['IGMC', 'CNV1', 'CNV2', 'CNV3', 'NGBUF', 'OLDBF', 'MAIN']
    db_saver = ContinuousDataSaver(
            continuous_data_table='dateplots_microreactorNG',
            username=credentials.username,
            password=credentials.password,
            measurement_codenames = ['microreactorng_valve_'+valve_names for valve_names in list(setpoint_channel_userlabel_on_off.keys())],
    )

    pressure_control = xgs600Control(port = port,
                                     socket_name = socket_name,
                                     codenames = codenames,
                                     devices = devices,
                                     valve_properties = setpoint_channel_userlabel_on_off,
                                     db_saver = db_saver,
                                     )
    pressure_control.start()
    time.sleep(1)

    while pressure_control.isAlive():
        time.sleep(0.25)

#    LOGGER.info('script ended')

if __name__ == '__main__':
    main()
