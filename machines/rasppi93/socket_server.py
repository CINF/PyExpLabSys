""" Flow control for Seljalandsfoss setup """
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
    devices = ['M11200362B']#, 'M11200362G']
    ranges = {}
    ranges['M11200362B'] = 1 # Flow 
    ranges['M11200362G'] = 1 # Flow

    flow_control = FlowControl(devices=devices, ranges=ranges,
                               socket_name='Seljalandsfoss_mfc_control')
    flow_control.start()

    logger = ValueLogger(flow_control, comp_val=1, comp_type='log', low_comp=0.0001)
    logger.start()
    ''' We need to update the date plot for Seljalandsfoss instead of the microreactor NG setup  '''
    #db_logger = ContinuousDataSaver(continuous_data_table='dateplots_microreactorNG',
    #                                username=credentials.user,
    #                                password=credentials.passwd,
    #                                measurement_codenames=['microreactorng_pressure_reactor'])
    #db_logger.start()

    time.sleep(5)
    while True:
        time.sleep(0.25)
        value = logger.read_value()
    ''' We need to update the date plot for Seljalandsfoss instead of the microreactor NG setup  '''
        #if logger.read_trigged():
            #print(value)
            #db_logger.save_point_now('microreactorng_pressure_reactor', value)
            #logger.clear_trigged()

if __name__ == '__main__':
    main()
