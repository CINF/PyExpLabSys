import threading
import Queue
import time
from datetime import datetime

import pyodbc

import nidaq
import xgs600


"""
quit = False
ion_gauge_pressure = 0
ion_pump_pressure = 0
turbo_pump_temp = 0

class XGSClass(threading.Thread):
	def run(self):
		global ion_gauge_pressure
		while not quit:
			time.sleep(0.5)
			press = xgs600.readAllPressures()
			try:
				ion_gauge_pressure = press[1]
			except:
				print "av"


class AnalogClass(threading.Thread):
	def run(self):
		global ion_pump_pressure
		global turbo_pump_temp
		while not quit:
			(ion_pump_pressure,turbo_pump_temp) = nidaq.readPressureAndTemperature()
				
				
P = XGSClass()
A = AnalogClass()
P.start()
A.start()

for i in range(0,50):
	time.sleep(0.25)
	print ion_gauge_pressure
	print ion_pump_pressure
	print turbo_pump_temp
quit = True

def sqlTime():
	sqltime = datetime.now().isoformat(' ')[0:19]
	return(sqltime)

def sqlInsert(query):
	try:
		#cnxn = pyodbc.connect('DSN=new_db')
		cnxn = pyodbc.connect('DSN=robertj')
		cursor = cnxn.cursor()
	except:
		print "Unable to connect to database"
		return()
	try:
		cursor.execute(query)
		cnxn.commit()
	except:
		print "SQL-error, query written below:"
		print query
	cnxn.close()
	

	

#sqlInsert("test")
"""
def writePressuresToFile():
	pressures = xgs600.readAllPressures()
	try:
		if pressures[1]>0:
			f = open('c:\pressures\main_chamber.pressure','w+')
			f.write(str(pressures[1]))
			f.close()
		#print pressures[1]
	except:
		print pressures



while True:
	writePressuresToFile()

"""
	
last_recorded_pressure = 0
last_recorded_press_time = 1
	
#Get the gauge pressure from the driver, set negetive pressure if an error is returned
pressures = xgs600.readAllPressures()
try:
	gauge_pressure = pressures[1]
except:
	gauge_pressure = -9

time_trigged = (time.time() - last_recorded_press_time) > 60
val_trigged = not (last_recorded_pressure * 0.9 < gauge_pressure < last_recorded_pressure * 1.1)
if (time_trigged or val_trigged) and gauge_pressure > 0:
	meas_time = sqlTime()
	gauge_pressure = "%.5g" % gauge_pressure
	gauge_sql = "insert into pressure_tof_iongauge set time=\"" +  meas_time + "\", pressure = " + gauge_pressure
	sqlInsert(gauge_sql)


#Get the analog measurements
(ionpump,turbo) = nidaq.readPressureAndTemperature()



ionpump_pressure = "%.5g" % ionpump
turbo_temp = "%.5g" % turbo
ionpump_sql =  "insert into pressure_tof_ionpump set time=\"" + meas_time + "\", pressure = " + ionpump_pressure
turbotemp_sql =  "insert into temperature_tof_turbopump set time=\""  + meas_time + "\", temperature = " + turbo_temp
sqlInsert(ionpump_sql)
sqlInsert(turbotemp_sql)


		
class PressClass(threading.Thread):
	def run(self):
		for j in range(0,5):
			#print nidaq.readPressureAndTemperature()
			q.put(nidaq.readPressureAndTemperature())
			
p = PressClass()
x = XGSClass()

q = Queue.Queue()


p.start()
x.start()

while True:
	item = q.get()
	print "Dav"
	print item
	q.task_done()
	
	
"""