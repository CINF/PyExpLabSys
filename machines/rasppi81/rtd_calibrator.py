""" Simple program to log the resistance of a micro-reactor """
from __future__ import print_function
import time
import PyExpLabSys.drivers.agilent_34972A as agilent_34972A
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


class RtdCalibrator(object):
    """ Simple class to log the resistance of a micro-reactor """
    def __init__(self, connection_string):
        self.mux = agilent_34972A.Agilent34972ADriver(interface='usbtmc',
                                                      connection_string=connection_string)
        self.data = {}
        self.data['2W Heater 1'] = None
        self.data['2W Heater 2'] = None
        self.data['2W RTD Source'] = None
        self.data['2W RTD Sense'] = None
        self.data['4W RTD'] = None
        self.data['Short circuit check'] = None
        self.data['RTD Source Sense Left'] = None
        self.data['RTD Source Sense Right'] = None
        self.data['Temperature'] = None

    def update_values(self):
        """ Update the current status of the reactor """
        comm_string = "CONFIGURE:RESISTANCE (@101,102,103,105,110,111,112)"
        self.mux.scpi_comm(comm_string)
        comm_string = "SENSE:RESISTANCE:NPLC 10, (@101,102,103,105,110,111,112)"
        self.mux.scpi_comm(comm_string)
        values = self.mux.read_single_scan()
        self.data['2W Heater 1'] = values[0]
        self.data['2W Heater 2'] = values[2]
        self.data['2W RTD Source'] = values[1]
        self.data['2W RTD Sense'] = values[6]
        self.data['Short circuit check'] = values[3]
        self.data['RTD Source Sense Left'] = values[4]
        self.data['RTD Source Sense Right'] = values[5]

        comm_string = "CONFIGURE:FRESISTANCE (@102)"
        self.mux.scpi_comm(comm_string)
        comm_string = "SENSE:FRESISTANCE:NPLC 100, (@102)"
        self.mux.scpi_comm(comm_string)
        values = self.mux.read_single_scan()
        self.data['4W RTD'] = values[0]

        comm_string = "CONFIGURE:TEMPERATURE (@104)"
        self.mux.scpi_comm(comm_string)
        values = self.mux.read_single_scan()
        self.data['Temperature'] = values[0]

        return True


    def start_measurement(self, comment):
        """ Start a measurement """
        data_set_saver = DataSetSaver("measurements_dummy", "xy_values_dummy",
                                      "dummy", "dummy")
        data_set_saver.start()
        data_set_time = time.time()

        metadata = {"Time": CustomColumn(data_set_time, "FROM_UNIXTIME(%s)"),
                    "comment": comment, "type": 65}

        labels = ["2W Heater 1", "2W Heater 2", "2W RTD Source", "2W RTD Sense",
                  "Short circuit check", "RTD Source Sense Left",
                  "RTD Source Sense Right", "4W RTD", "Temperature"]
        
        for label in labels:
            metadata["mass_label"] = label
            data_set_saver.add_measurement(label, metadata)

        for _ in range(0, 2):
            self.update_values()
            for label in labels:
                print('Channel: ' + label + ': ' + str(self.data[label]))
                data_set_saver.save_point(label, (time.time() - data_set_time,
                                                  self.data[label]))
            time.sleep(1)


    
if __name__ == '__main__':
    CALIBRATOR = RtdCalibrator('USB0::0x0957::0x2007::MY57000209::INSTR')
    CALIBRATOR.update_values()
    print(CALIBRATOR.data)

    CALIBRATOR.start_measurement(comment='R/T test')
