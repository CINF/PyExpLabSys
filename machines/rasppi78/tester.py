import time
import PyExpLabSys.drivers.agilent_34972A as agilent_34972A
import PyExpLabSys.drivers.keithley_smu as keithley_smu
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn

mux = agilent_34972A.Agilent34972ADriver(interface='usbtmc',
                                         connection_string='USB0::0x0957::0x2007::MY49011193::INSTR')

smu = keithley_smu.KeithleySMU(interface='serial', device='/dev/ttyUSB0', baudrate=9600)

print(smu.read_software_version())
print(mux.read_software_version())


#print(mux.read_configuration())

#mux.set_scan_list(['101,102,103,104,105,106,107,108'])

#comm_string = "CONFIGURE:VOLT (@101,102,103,104,105,106,107,108)"
#comm_string = "CONFIGURE:RESISTANCE (@101,102,103,104,105,106,107,108)"
#mux.scpi_comm(comm_string)

#mux.scpi_comm('INSTRUMENT:DMM OFF')
#print(mux.scpi_comm('INSTRUMENT:DMM?'))

#print(mux.read_single_scan())

print(mux.scpi_comm('ROUTE:CHAN:ADV:SOUR?'))

mux.scpi_comm('ROUTE:CLOSE (@101)')

time.sleep(0.2)

#print(smu.read_voltage())
smu.output_state(True)
smu.set_voltage(0.01)
current = smu.read_current()
print(current)
print(0.01/current)

comment = 'IV-test'
data_set_saver = DataSetSaver("measurements_dummy", "xy_values_dummy", "dummy", "dummy")
data_set_saver.start()
data_set_time = time.time()
metadata = {"Time": CustomColumn(data_set_time, "FROM_UNIXTIME(%s)"), "comment": comment,
            "type": 1, "preamp_range": 0, "sem_voltage": 0}
for label in ["Ch1", "Ch2", "Ch3", "Ch4", "Ch5", "Ch6", "Ch7", "Ch8",]:
    metadata["mass_label"] = label
    data_set_saver.add_measurement(label, metadata)

for channel in range(1, 9):
    print('Channel: ' + str(channel))
    mux.scpi_comm('ROUTE:CLOSE (@10' + str(channel) + ')' )
    time.sleep(0.2)
    V, I = smu.iv_scan(-0.2, 0.2, 0.001)    
    for i in range(0, len(I)):
        data_set_saver.save_point('Ch' + str(channel), (V[i], I[i]))
    mux.scpi_comm('ROUTE:OPEN (@10' + str(channel) + ')' )
    time.sleep(0.2)

time.sleep(1)
mux.scpi_comm('ROUTE:CLOSE (@101)')
