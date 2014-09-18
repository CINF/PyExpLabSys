import threading
import Queue
import time
from datetime import datetime
import serial
import sys
#sys.path.append('../')
import MySQLdb


import NGC2D as NGC2D
import omegabus as OmegaBus

def sqlTime():
	sqltime = datetime.now().isoformat(' ')[0:19]
	return(sqltime)

def sqlInsert(query):
	try:
		cnxn = MySQLdb.connect(host="servcinf",user="omicron",passwd="omicron",db="cinfdata")
		#cnxn = pyodbc.connect('DSN=new_db')
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
        def __init__(self):
                threading.Thread.__init__(self)
                self.NGC2D = NGC2D.NGC2D_comm('/dev/ttyUSB1')
                #self.NGC2D = NGC2D.NGC2D_comm()
        def run(self):
                global ion_gauge_pressure
                while not quit:
                        time.sleep(1)
                        press = self.NGC2D.ReadPressure()
                        #print press
                        try:
                                ion_gauge_pressure = float(press)
                                isinstance(press, float)
                        except:
                                print "av-NGC2DClass"

class OmegaBusClass(threading.Thread):
        def __init__(self):
                threading.Thread.__init__(self)
                self.omega = OmegaBus.OmegaBus('/dev/ttyUSB0')
	def run(self):
		global temp_oldclustersource
		global temp_nanobeam
		while not quit:
			time.sleep(1)
			temp0 = self.omega.ReadValue(1)# + 273.15
			#print 'temp 0: ' + str(temp0)
			time.sleep(1)
			temp1 = self.omega.ReadValue(2)# + 273.15
			#print 'temp 1: ' + str(temp1)
			#time.sleep(1)
			#temp2 = self.omega.ReadValue(2)# + 273.15
			#print 'temp 2: ' + str(temp2)
			#time.sleep(1)
			#temp3 = self.omega.ReadValue(3)# + 273.15
			#print 'temp 3: ' + str(temp3)
			try:
				temp_nanobeam = temp0
				isinstance(temp0, float)
				temp_oldclustersource = temp1
				isinstance(temp1, float)
			except:
				print "av-OmegaBusClass"

class NGC2DSaver(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.last_recorded_value = 0
		self.last_recorded_time = 1
	
	def run(self):
		while not quit:
			time.sleep(1)
			time_trigged = (time.time() - self.last_recorded_time) > 30
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
				sql_statement = "insert into pressure_omicron_nanobeam set time=\"" +  meas_time + "\", pressure = " + val
				print sql_statement
				sqlInsert(sql_statement)

class temp_oldclustersource_Saver(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.last_recorded_value = 0
		self.last_recorded_time = 1
	
	def run(self):
		while not quit:
			time.sleep(1)
			time_trigged = (time.time() - self.last_recorded_time) > 30
			val_trigged = not (self.last_recorded_value - 2.0 < temp_oldclustersource < self.last_recorded_value + 2)
			if (time_trigged or val_trigged) and temp_oldclustersource < 300:
				self.last_recorded_value = temp_oldclustersource
				self.last_recorded_time = time.time()
				meas_time = sqlTime()
				val = "%.5g" % temp_oldclustersource
				sql_statement = "insert into temperature_oldclusterce_aggregation set time=\"" +  meas_time + "\", temperature = " + val
				print sql_statement
				#sqlInsert(sql_statement)

class temp_nanobeam_Saver(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.last_recorded_value = 0
		self.last_recorded_time = 1
	
	def run(self):
		while not quit:
			time.sleep(1)
			time_trigged = (time.time() - self.last_recorded_time) > 30
			val_trigged = not (self.last_recorded_value - 2.0 < temp_nanobeam < self.last_recorded_value + 2.0)
			if (time_trigged or val_trigged) and temp_nanobeam < 300:
				self.last_recorded_value = temp_nanobeam
				self.last_recorded_time = time.time()
				meas_time = sqlTime()
				val = "%.5g" % temp_nanobeam
				sql_statement = "insert into temperature_omicron_nanobeam_aggregation set time=\"" +  meas_time + "\", temperature = " + val
				print sql_statement
				sqlInsert(sql_statement)
		

quit = False
ion_gauge_pressure = -1
temp_oldclustersource = 1000
temp_nanobeam = 1000

	
P = NGC2DClass()
O = OmegaBusClass()

PressSaver = NGC2DSaver()
TempSaver0 = temp_oldclustersource_Saver()
TempSaver1 = temp_nanobeam_Saver()

P.start()
O.start()

PressSaver.start()
TempSaver0.start()
TempSaver1.start()

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
