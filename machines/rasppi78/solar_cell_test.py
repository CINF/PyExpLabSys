""" Script to perform systematic solar cell tests """
from __future__ import print_function
import time
import PyExpLabSys.drivers.agilent_34972A as agilent_34972A
import PyExpLabSys.drivers.keithley_smu as keithley_smu
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class SolarCellTester(object):
    """ Performs an IV test """
    def __init__(self, mux, smu, comment, user):
        self.data_set_saver = DataSetSaver("measurements_" + user,
                                           "xy_values_" + user, user, user)
        self.data_set_saver.start()
        self.data_set_time = time.time() # Update for each scan...
        self.comment = comment
        self.mux = mux
        self.smu = smu
        mux.scpi_comm('INSTRUMENT:DMM OFF') # Turn off DMM to allow use as mux device
        self.smu.set_current_limit(0.01) # Current limit, 10mA
        self.smu.set_current_measure_range(current_range=0.01) # Measurement range 10mA
        self.smu.set_integration_time(1)

    def run_measurement(self, v_from, v_to, scan_both_ways):
        """ Perform the actual measurement """
        metadata = {"Time": CustomColumn(self.data_set_time, "FROM_UNIXTIME(%s)"),
                    "comment": self.comment, "type": 1}
        for label in ["Ch1", "Ch2", "Ch3", "Ch4", "Ch5", "Ch6", "Ch7", "Ch8",]:
            metadata["mass_label"] = label
            self.data_set_saver.add_measurement(label, metadata)

        self.smu.set_voltage(0.0)
        self.smu.output_state(True)
        for channel in range(1, 9):
            print('Channel: ' + str(channel))
            self.mux.scpi_comm('ROUTE:CLOSE (@10' + str(channel) + ')')
            time.sleep(0.2)

            voltage, current = self.smu.iv_scan(v_from=v_from, v_to=v_to,
                                                steps=10, settle_time=0)
            for i in range(0, len(current)):
                self.data_set_saver.save_point('Ch' + str(channel), (voltage[i], current[i]))

            if scan_both_ways:
                voltage, current = self.smu.iv_scan(v_from=v_to, v_to=v_from,
                                                    steps=50, settle_time=0)
                for i in range(0, len(current)):
                    self.data_set_saver.save_point('Ch' + str(channel),
                                                   (voltage[i], current[i]))

            self.mux.scpi_comm('ROUTE:OPEN (@10' + str(channel) + ')')
        self.smu.set_voltage(0.0)
        self.smu.output_state(False)
        time.sleep(0.2)


def main():
    """ Main Function """
    conn_string = 'USB0::0x0957::0x2007::MY49011193::INSTR'
    mux = agilent_34972A.Agilent34972ADriver(interface='usbtmc',
                                             connection_string=conn_string)
    print(mux.read_software_version())

    smu = keithley_smu.KeithleySMU(interface='serial', device='/dev/ttyUSB0', baudrate=9600)
    print(smu.read_software_version())

    time.sleep(0.2)

    iv_test = SolarCellTester(mux, smu, COMMENT, credentials.user)
    iv_test.run_measurement(V_FROM, V_TO, SCAN_BOTH_WAYS)

if __name__ == '__main__':
    V_FROM = -1.1
    V_TO = 0
    SCAN_BOTH_WAYS = True
    COMMENT = 'IV-test 3'

    main()
