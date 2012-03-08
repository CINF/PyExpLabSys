import threading
import Queue
import time
from datetime import datetime

import pyodbc

import nidaq
import xgs600


def sqlTime():
	sqltime = datetime.now().isoformat(' ')[0:19]
	return(sqltime)

def sqlInsert(query):
	try:
		cnxn = pyodbc.connect('DSN=new_db')
		#cnxn = pyodbc.connect('DSN=robertj')
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

class XGSSaver(threading.Thread):
	
	def __init__(self):
		threading.Thread.__init__(self)
		self.last_recorded_value = 0
		self.last_recorded_time = 1
	
	def run(self):
		while not quit:
			time.sleep(1)
			time_trigged = (time.time() - self.last_recorded_time) > 60
			val_trigged = not (self.last_recorded_value * 0.9 < ion_gauge_pressure < self.last_recorded_value * 1.1)
			#print (time.time() - self.last_recorded_time)
			if (time_trigged or val_trigged) and ion_gauge_pressure > 0:
				self.last_recorded_value = ion_gauge_pressure
				self.last_recorded_time = time.time()
				meas_time = sqlTime()
				val = "%.5g" % ion_gauge_pressure
				gauge_sql = "insert into pressure_tof_iongauge set time=\"" +  meas_time + "\", pressure = " + val
				print gauge_sql
				sqlInsert(gauge_sql)
		
class IonPumpSaver(threading.Thread):
	
	def __init__(self):
		threading.Thread.__init__(self)
		self.last_recorded_value = 0
		self.last_recorded_time = 1
	
	def run(self):
		while not quit:
			time.sleep(1)
			time_trigged = (time.time() - self.last_recorded_time) > 60
			val_trigged = not (self.last_recorded_value * 0.9 < ion_pump_pressure < self.last_recorded_value * 1.1)
			#print (time.time() - self.last_recorded_time)
			if (time_trigged or val_trigged) and (ion_pump_pressure > 0):
				self.last_recorded_value = ion_pump_pressure
				self.last_recorded_time = time.time()
				meas_time = sqlTime()
				val = "%.5g" % ion_pump_pressure
				gauge_sql = "insert into pressure_tof_ionpump set time=\"" +  meas_time + "\", pressure = " + val
				print gauge_sql
				sqlInsert(gauge_sql)

class TurboTempSaver(threading.Thread):
	
	def __init__(self):
		threading.Thread.__init__(self)
		self.last_recorded_value = 0
		self.last_recorded_time = 1
	
	def run(self):
		while not quit:
			time.sleep(1)
			time_trigged = (time.time() - self.last_recorded_time) > 60
			val_trigged = not ((self.last_recorded_value - 0.5) < turbo_pump_temp < (self.last_recorded_value + 0.5))
			#print (time.time() - self.last_recorded_time)
			if (time_trigged or val_trigged) and (turbo_pump_temp > 0):
				self.last_recorded_value = turbo_pump_temp
				self.last_recorded_time = time.time()
				meas_time = sqlTime()
				val = "%.5g" % turbo_pump_temp
				gauge_sql = "insert into temperature_tof_turbopump set time=\"" +  meas_time + "\", temperature = " + val
				print gauge_sql
				sqlInsert(gauge_sql)

				
quit = False
ion_gauge_pressure = 0
ion_pump_pressure = 0
turbo_pump_temp = 0

	
P = XGSClass()
A = AnalogClass()
PressSaver = XGSSaver()
IonSaver = IonPumpSaver()
TurboSaver = TurboTempSaver()
P.start()
A.start()
PressSaver.start()
IonSaver.start()
TurboSaver.start()

while not quit:
	try:
		time.sleep(1)
		#print "Ion Gauge: " + "%.5g" % ion_gauge_pressure
		#print "Ion Pump: " +  "%.5g" % ion_pump_pressure
		#print "Turbo Temperature: " +  "%.5g" % turbo_pump_temp
	except:
		quit = True


"""
	

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