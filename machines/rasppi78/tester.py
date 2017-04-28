import time
import PyExpLabSys.drivers.agilent_34972A as agilent_34972A
import PyExpLabSys.drivers.keithley_smu as keithley_smu

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
