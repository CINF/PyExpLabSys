""" Control app for analog pressure controller on sniffer setup """
from __future__ import print_function
import time
from PyExpLabSys.common.analog_flow_control import AnalogMFC
from PyExpLabSys.common.analog_flow_control import FlowControl
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
import credentials

def main():
    """ Main function """

    codenames = ['sniffer_inlet_gas_pressure']
    mfc = AnalogMFC(1, 10, 5)
    mfcs = {}
    mfcs[codenames[0]] = mfc

    flow_control = FlowControl(mfcs, 'sniffer')
    flow_control.start()

    loggers = {}
    loggers[codenames[0]] = ValueLogger(flow_control, comp_val=0.02, comp_type='lin',
                                        low_comp=0.01, channel=codenames[0])
    loggers[codenames[0]].start()
    
    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_sniffer',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    while True:
        time.sleep(0.5)
        for name in codenames:
            if loggers[name].read_trigged():
                print(name + ': ' + str(loggers[name].value))
                db_logger.save_point_now(name, loggers[name].value)
                loggers[name].clear_trigged()

if __name__ == '__main__':
    main()
