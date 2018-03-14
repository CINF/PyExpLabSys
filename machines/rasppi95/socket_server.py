""" Flow controller for microreactor Bronkhorst devices """
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
    devices = ['M13201551A', 'M11200362F', 'M8203814A', 'M8203814B',
               'M11200362B', 'M11213502A']
    ranges = {}
    ranges['M13201551A'] = 5 # Microreactor, pressure controller
    ranges['M11200362F'] = 1 # Microreactor, flow 2
    ranges['M8203814A'] = 10 # Microreactor, flow 5 (argon calibrated)
    ranges['M8203814B'] = 3 # Microreactor, flow 1 (argon calibrated)

    flow_control = FlowControl(devices=devices, ranges=ranges, name='microreactor_mfc_control')
    flow_control.start()

    logger = ValueLogger(flow_control, comp_val=1, comp_type='log', low_comp=0.0001)
    logger.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_microreactor',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=['mr_reactor_pressure'])
    db_logger.start()

    time.sleep(5)
    while True:
        time.sleep(0.25)
        value = logger.read_value()
        if logger.read_trigged():
            print(value)
            db_logger.save_point_now('mr_reactor_pressure', value)
            logger.clear_trigged()


if __name__ == '__main__':
    main()
