""" Simple program to log the resistance of a micro-reactor """
from __future__ import print_function
import time
import socket
import PyExpLabSys.drivers.keithley_smu as keithley_smu
import PyExpLabSys.drivers.agilent_34972A as agilent_34972A
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


class RtdCalibrator(object):
    """ Simple class to log the resistance of a micro-reactor """
    def __init__(self, connection_string, temperature_host=None, only_4w=False, use_smu=True):
        self.mux = agilent_34972A.Agilent34972ADriver(interface='usbtmc',
                                                      connection_string=connection_string)
        self.smu = keithley_smu.KeithleySMU(interface='serial', device='/dev/ttyUSB0', baudrate=4800)
        self.temperature_host = temperature_host
        self.only_4w = only_4w
        self.use_smu = use_smu
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
        self.data['Temperature 2'] = None
        comm_string = "CONFIGURE:FRESISTANCE (@102)"
        self.mux.scpi_comm(comm_string)
        comm_string = "SENSE:FRESISTANCE:NPLC 100, (@102)"
        self.mux.scpi_comm(comm_string)

    def update_values(self):
        """ Update the current status of the reactor """
        if self.only_4w is False:
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
        else:
            self.data['2W Heater 1'] = 0
            self.data['2W Heater 2'] = 0
            self.data['2W RTD Source'] = 0
            self.data['2W RTD Sense'] = 0
            self.data['Short circuit check'] = 0
            self.data['RTD Source Sense Left'] = 0
            self.data['RTD Source Sense Right'] = 0
            self.data['4W RTD'] = 0

        if self.use_smu is False:
            values = self.mux.read_single_scan()
            self.data['4W RTD'] = values[0]
        else:
            #self.smu.set_integration_time(100, 1)
            #self.smu.set_integration_time(100, 2)
            t = time.time()
            source_current = self.smu.read_current(1)
            source_voltage = self.smu.read_voltage(1)
            probe_voltage = self.smu.read_voltage(2)
            print(time.time() - t)
            print(source_current, source_voltage, probe_voltage)
            self.data['2W RTD Source'] = source_voltage / source_current
            self.data['4W RTD'] = probe_voltage / source_current


        if self.temperature_host is None:
            comm_string = "CONFIGURE:TEMPERATURE (@104)"
            self.mux.scpi_comm(comm_string)
            values = self.mux.read_single_scan()
            self.data['Temperature'] = values[0]
        else:
            data_temp = b'fr307_furnace_1_T#raw'
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            sock.sendto(data_temp, (self.temperature_host, 9001))
            received = sock.recv(1024).decode()
            self.data['Temperature'] = float(received[received.find(',') + 1:])

            data_temp = b'fr307_furnace_2_T#raw'
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            sock.sendto(data_temp, (self.temperature_host, 9001))
            received = sock.recv(1024).decode()
            self.data['Temperature 2'] = float(received[received.find(',') + 1:])
        return True


    def start_measurement(self, comment):
        """ Start a measurement """
        data_set_saver = DataSetSaver("measurements_dummy", "xy_values_dummy",
                                      "dummy", "dummy")
        data_set_saver.start()
        data_set_time = time.time()

        metadata = {"Time": CustomColumn(data_set_time, "FROM_UNIXTIME(%s)"),
                    "comment": comment, "type": 65,
                    "preamp_range": 9, "sem_voltage": -1}

        labels = ["2W Heater 1", "2W Heater 2", "2W RTD Source", "2W RTD Sense",
                  "Short circuit check", "RTD Source Sense Left",
                  "RTD Source Sense Right", "4W RTD", "Temperature", "Temperature 2"]
        
        for label in labels:
            metadata["mass_label"] = label
            data_set_saver.add_measurement(label, metadata)

        for i in range(0, 99999999):
            self.update_values()
            for label in labels:
                print(str(i) + ': Channel: ' + label + ': ' + str(self.data[label]))
                data_set_saver.save_point(label, (time.time() - data_set_time,
                                                  self.data[label]))
            time.sleep(1)


    
if __name__ == '__main__':
    #CALIBRATOR = RtdCalibrator('USB0::0x0957::0x2007::MY57000209::INSTR', temperature_host='rasppi88')
    CALIBRATOR = RtdCalibrator('USB0::0x0957::0x2007::MY57000209::INSTR', only_4w=True, use_smu=True,
                               temperature_host='rasppi88')
    for i in range(0, 1):
        CALIBRATOR.update_values()
        print(CALIBRATOR.data)
        

    CALIBRATOR.start_measurement(comment='3.2 - 5.0mA')
