import threading
import Queue
import time
import datetime
import serial

import pyodbc

#import nidaq
import NGC2D


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

class NGC2DClass(threading.Thread):
	def run(self):
		global ion_gauge_pressure
		while not quit:
			time.sleep(0.5)
			press = NGC2D.ReadPressure()
			#print press
			try:
				ion_gauge_pressure = press
				isinstance(press, float)
			except:
				print "av"

class NGC2DSaver(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.last_recorded_value = 0
		self.last_recorded_time = 1
	
	def run(self):
		while not quit:
			time.sleep(1)
			time_trigged = (time.time() - self.last_recorded_time) > 300
			#print time_trigged
			val_trigged = not (self.last_recorded_value * 0.9 < ion_gauge_pressure < self.last_recorded_value * 1.1)
                        #print val_trigged
			#print (time.time() - self.last_recorded_time)
			#print ion_gauge_pressure
			if (time_trigged or val_trigged) and ion_gauge_pressure > 0:
				self.last_recorded_value = ion_gauge_pressure
				self.last_recorded_time = time.time()
				meas_time = sqlTime()
				val = "%.5g" % ion_gauge_pressure
				gauge_sql = "insert into pressure_omicron_nanobeam set time=\"" +  meas_time + "\", pressure = " + val
				print gauge_sql
				sqlInsert(gauge_sql)
		

quit = False
ion_gauge_pressure = 0
#ion_pump_pressure = 0
#turbo_pump_temp = 0

	
P = NGC2DClass()
#A = AnalogClass()
PressSaver = NGC2DSaver()
#IonSaver = IonPumpSaver()
#TurboSaver = TurboTempSaver()
P.start()
#A.start()
PressSaver.start()
#IonSaver.start()
#TurboSaver.start()

while not quit:
	try:
		time.sleep(1)
		#print "Ion Gauge: " + "%.5g" % ion_gauge_pressure
		#print "Ion Pump: " +  "%.5g" % ion_pump_pressure
		#print "Turbo Temperature: " +  "%.5g" % turbo_pump_temp
	except:
		quit = True
