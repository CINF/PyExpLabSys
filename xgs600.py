import serial
import time

def xgs_comm(command,port=0):
	ser = serial.Serial(0)
	comm = "#00" + command + "\r"

	ser.write(comm)
	time.sleep(1.0)
	bytes = ser.inWaiting()
	complete_string = ser.read(bytes)

	ser.close()

	complete_string = complete_string.replace('>','').replace('\r','')
	return(complete_string)


def readAllPressures():
	pressure_string = xgs_comm("0F")
	#print pressure_string
	if len(pressure_string)>0:
		temp_pressure = pressure_string.replace(' ','').split(',')

		pressures = []
		for press in temp_pressure:
			if press == 'OPEN':
				pressures.append(-1)
			else:
				try:
					pressures.append((float)(press))
				except:
					pressures.append(-2)
	else:
		pressures = [-3]
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


def readSoftwareVersion():
	gauge_string = xgs_comm("05")
	return(gauge_string)


def readPressureUnit():
	gauge_string = xgs_comm("13")
	unit = gauge_string.replace(' ','')
	if unit == "00":
		unit = "Torr"
	if unit == "01":
		unit = "mBar"
	if unit == "02":
		unit = "Pascal"
	return(unit)





#print readAllPressures()

#print listAllGauges()