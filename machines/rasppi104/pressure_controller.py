""" Pressure xgs600 controller for microreactors """
from __future__ import print_function
import time
import credentials
from PyExpLabSys.common.pressure_controller_xgs600 import XGS600Control
import PyExpLabSys.common.utilities
#from PyExpLabSys.common.utilities import get_logger
#from PyExpLabSys.common.utilities import activate_library_logging
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.supported_versions import python3_only
PyExpLabSys.common.utilities.ERROR_EMAIL = 'alexkbb@fysik.dtu.dk'
python3_only(__file__)


MICRO = chr(0x03BC) # Python 3

#### UPDATE  PRESSURE CONTROL LOGGING ####

#LOGGER = get_logger(MICRO + '-reactorNG XGS600 control', level='ERROR', file_log=True,
#                    file_name='XGS600_control.log', terminal_log=False, email_on_warnings=False)
#activate_library_logging('PyExpLabSys.common.microreactor_temperature_control',
#                         logger_to_inherit_from=LOGGER)
#activate_library_logging('PyExpLabSys.auxiliary.pid', logger_to_inherit_from=LOGGER)

#LOGGER.warn('Program started')

def main():
    """ Main function """
    port = '/dev/ttyUSB0'
    codenames = ['pressure', 'state']
    socket_name = MICRO + '-reactorANH_xgs600_pressure_control'
    setpoint_channel_userlabel_on_off = {
        'T1': [1, 'NGBUF', '1.333E-04', '2.000E+00'],
        'T2': [2, 'IGMC', '1.000E-11', '1.000E-05'],
        'T3': [3, 'NGBUF', '1.333E-04', '1.000E+00'],
        }
    user_labels = ['IGMC', 'CNV1', 'CNV2', 'CNV3', 'NGBUF', 'OLDBF', 'MAIN']
    db_saver = ContinuousDataSaver(
        continuous_data_table='dateplots_microreactorNG',
        username=credentials.username,
        password=credentials.password,
        measurement_codenames=\
            ['microreactorng_valve_'+valve_names for valve_names \
            in list(setpoint_channel_userlabel_on_off.keys())],
    )

    pressure_control = XGS600Control(port=port,
                                     socket_name=socket_name,
                                     codenames=codenames,
                                     user_labels=user_labels,
                                     valve_properties=setpoint_channel_userlabel_on_off,
                                     db_saver=db_saver,
                                     )
    pressure_control.start()
    time.sleep(1)

    while pressure_control.isAlive():
        time.sleep(0.25)

#    LOGGER.info('script ended')

if __name__ == '__main__':
    main()
