import time
import PyExpLabSys.drivers.agilent_34972A as agilent_34972A
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn

mux = agilent_34972A.Agilent34972ADriver(interface='usbtmc',
                                         connection_string='USB0::0x0957::0x2007::MY57000209::INSTR')



#print(mux.read_configuration())

#mux.set_scan_list(['101,102,103,104,105,106,107,108'])

#comm_string = "CONFIGURE:VOLT (@101,102,103,104,105,106,107,108)"
comm_string = "CONFIGURE:RESISTANCE (@101,102,103,105,110,111,112)"
mux.scpi_comm(comm_string)
wire_2 = mux.read_single_scan()

comm_string = "CONFIGURE:FRESISTANCE (@102)"
mux.scpi_comm(comm_string)
wire_4 = mux.read_single_scan()

comm_string = "CONFIGURE:TEMPERATURE (@104)"
mux.scpi_comm(comm_string)
temperature = mux.read_single_scan()

print('Heater 1, 2W: ' + str(wire_2[0]))
print('Heater 2, 2W: ' + str(wire_2[2]))
print('RTD Probe, 2W: ' + str(wire_2[1]))
print('RTD Sense, 2W: ' + str(wire_2[6]))
print('RTD, 4W: ' + str(wire_4[0]))
print('Short circuit-check: ' + str(wire_2[3]))
print('RTD Probe-sense left, 2W: ' + str(wire_2[4]))
print('RTD Probe-sense left, 2W: ' + str(wire_2[5]))
print('Temperature: ' + str(temperature[0]))



time.sleep(0.2)


"""
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
"""
