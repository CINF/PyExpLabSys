import serial
import time

def xgs_comm(command,port=0):
	ser = serial.Serial(0)
	comm = "#00" + command

	ser.write(comm)
	time.sleep(0.25)
	bytes = ser.inWaiting()
	ser.read(bytes) # Strange, if the command is different from last command, it needs to be send twice...

	ser.write(comm)
	time.sleep(0.25)
	bytes = ser.inWaiting()
	complete_string = ser.read(bytes)

	ser.close()

	complete_string = complete_string.replace('>','').replace('\r','')
	return(complete_string)


def readAllPressures():
	pressure_string = xgs_comm("0F")

	temp_pressure = pressure_string.replace(' ','').split(',')
	pressures = []
	for press in temp_pressure:
		if press == 'OPEN':
			pressures.append(-1)
		else:
			pressures.append((float)(press))
	return(pressures)

def listAllGauges():
	gauge_string = xgs_comm("01")

	gauges = ""
	for i in range(0,len(gauge_string),2):
		gauge = gauge_string[i:i+2]
		if gauge == "10":
			gauges = gauges + str(i/2) + ": Hot Filament Gauge\n"
		if gauge == "FE":
			gauges = gauges + str(i/2) + ": Empty Slot\n"
		if gauge == "40":
			gauges = gauges + str(i/2) + ": Convection Board\n"
		if gauge == "3A":
			gauges = gauges + str(i/2) + ": Inverted Magnetron Board\n"


	return(gauges)


def writePressuresToFile():
	pressures = readAllPressures()
	f = open('c:\pressures\main_chamber.pressure','w+')
	f.write(str(pressures[1]))
	print pressures[1]
	f.close()


while True:
	writePressuresToFile()

#print readAllPressures()

#print listAllGauges()