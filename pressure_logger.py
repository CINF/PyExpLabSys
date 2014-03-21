import threading
import Queue
import time
from datetime import datetime
import MySQLdb
import xgs600


def sqlTime():
    sqltime = datetime.now().isoformat(' ')[0:19]
    return(sqltime)

def sqlInsert(query):
    try:
        cnxn = MySQLdb.connect(host="servcinf",user="tof",passwd="tof",db="cinfdata")
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
    def __init__(self):
        threading.Thread.__init__(self)
        self.xgs = xgs600.XGS600Driver()

    def run(self):
        global ion_gauge_pressure
        global flighttube_pressure
        while not quit:
            time.sleep(2.5)
	    press = self.xgs.read_all_pressures()
	    try:
                ion_gauge_pressure = press[1]
                flighttube_pressure = press[0]
	    except:
		print "av"

class IonGaugeSaver(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
	self.last_recorded_value = -1
	self.last_recorded_time = 1
	
    def run(self):
	while not quit:
            time.sleep(1)
	    time_trigged = (time.time() - self.last_recorded_time) > 60
            val_trigged = not (self.last_recorded_value * 0.9 < ion_gauge_pressure < self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged) and ion_gauge_pressure > 0:
                self.last_recorded_value = ion_gauge_pressure
		self.last_recorded_time = time.time()
		meas_time = sqlTime()
		val = "%.5g" % ion_gauge_pressure
		gauge_sql = "insert into dateplots_tof set type=\"P_iongauge\", time=\"" +  meas_time + "\", value = " + val
		print gauge_sql
		sqlInsert(gauge_sql)

class FlighttubeSaver(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
	self.last_recorded_value = -1
	self.last_recorded_time = 1
	
    def run(self):
	while not quit:
            time.sleep(1)
	    time_trigged = (time.time() - self.last_recorded_time) > 60
            val_trigged = not (self.last_recorded_value * 0.9 < flighttube_pressure < self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged) and flighttube_pressure > 0:
                self.last_recorded_value = flighttube_pressure
		self.last_recorded_time = time.time()
		meas_time = sqlTime()
		val = "%.5g" % flighttube_pressure
		gauge_sql = "insert into dateplots_tof set type=\"P_flighttube\", time=\"" +  meas_time + "\", value = " + val
		print gauge_sql
		sqlInsert(gauge_sql)
		
				
quit = False
ion_gauge_pressure = 0
flighttube_pressure = 0

P = XGSClass()
gaugesaver = IonGaugeSaver()
tubesaver = FlighttubeSaver()
P.start()
time.sleep(2)
print 'a'
gaugesaver.start()
print 'a'
tubesaver.start()
print 'a'


while not quit:
	try:
		time.sleep(1)
		#print "Ion Gauge: " + "%.5g" % ion_gauge_pressure
		#print "Ion Pump: " +  "%.5g" % ion_pump_pressure
		#print "Turbo Temperature: " +  "%.5g" % turbo_pump_temp
	except:
		quit = True

