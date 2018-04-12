""" Flow control for microreactor NG setup """
from __future__ import print_function
import time
from PyExpLabSys.common.flow_control_bronkhorst import FlowControl
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

def main():
    """ Main function """
    devices = ['M11200362H', 'M11200362C', 'M11200362A',
               'M11200362E', 'M11200362D', 'M11210022B', 'M11200362G']
    ranges = {}
    ranges['M11200362H'] = 2.5 # Pressure controller
    ranges['M11200362C'] = 10 # Flow1
    ranges['M11200362A'] = 10 # Flow2
    ranges['M11200362E'] = 5 # Flow3
    ranges['M11200362D'] = 5 # Flow4
    ranges['M11210022B'] = 10 # Flow5 (NH3 compatible)
    ranges['M11200362G'] = 1 # Flow6

    flow_control = FlowControl(devices=devices, ranges=ranges,
                               socket_name='microreactorNG_mfc_control')
    flow_control.start()

    logger = ValueLogger(flow_control, comp_val=1, comp_type='log', low_comp=0.0001)
    logger.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_microreactorNG',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=['microreactorng_pressure_reactor'])
    db_logger.start()

    time.sleep(5)
    while True:
        time.sleep(0.25)
        value = logger.read_value()
        if logger.read_trigged():
            print(value)
            db_logger.save_point_now('microreactorng_pressure_reactor', value)
            logger.clear_trigged()

if __name__ == '__main__':
    main()
