""" XPS Module """
import time
import threading
import numpy as np
import PyExpLabSys.drivers.agilent_34972A as agilent_34972A
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

class XPS(threading.Thread):
    """ Perform a single XPS scan """
    def __init__(self, hostname, anode):
        threading.Thread.__init__(self)

        self.agilent = agilent_34972A.Agilent34972ADriver(interface='lan', hostname=hostname)
        self.calib = 500  # Analyser voltage pr. input voltage
        self.chamber_name = "dummy"
        self.data_set_saver = DataSetSaver("measurements_" + self.chamber_name,
                                           "xy_values_" + self.chamber_name,
                                           credentials.user, credentials.passwd)
        self.data_set_saver.start()

        if anode == 'Mg':
            self.x_ray = 1253.44
        if anode == 'Al':
            self.x_ray = 1487.0

    def scan(self, start_energy, end_energy, step, integration_time):
        """ Perform a scan  """
        metadata = {"Time": CustomColumn(time.time(), "FROM_UNIXTIME(%s)"),
                    "comment": 'Test', "type": 2}

        label = 'XPS signal'
        self.data_set_saver.add_measurement(label, metadata)

        count_string = self.agilent.scpi_comm("SENS:TOT:DATA? (@203)")
        meas_time = time.time()
        for binding_energy in np.arange(end_energy, start_energy, -1 * step):
            kin_energy = str((self.x_ray - binding_energy) / self.calib)
            string = "SOURCE:VOLT " + kin_energy + ", (@205)"
            self.agilent.scpi_comm(string)

            time.sleep(integration_time)

            count_string = self.agilent.scpi_comm("SENS:TOT:DATA? (@203)")
            count = int(float(count_string.strip()))
            int_time = time.time() - meas_time
            meas_time = time.time()

            count_rate = count / int_time
            self.data_set_saver.save_point(label, (binding_energy, count_rate))


def main():
    """ Main function """
    xps = XPS('volvo-agilent-34972a', 'Al')
    xps.scan(540, 545, step=0.1, integration_time=1.0)

if __name__ == "__main__":
    main()
