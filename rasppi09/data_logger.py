import threading
import Queue
import time
from datetime import datetime
import MySQLdb
import xgs600
import socket

def set_pressure(value):
    print value
    HOST, PORT = "rasppi09", 9999
    data = "set_iongauge " + str(value)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data + "\n", (HOST, PORT))
    received = sock.recv(1024)
    return_val = False
    if received == "ok":
        return_val = True
    return return_val

def sqlTime():
    sqltime = datetime.now().isoformat(' ')[0:19]
    return(sqltime)

def sqlInsert(query):
    try:
        cnxn = MySQLdb.connect(host="servcinf",user="NH3Synth",passwd="NH3Synth",db="cinfdata")
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
        while not quit:
            time.sleep(2.5)
	    press = self.xgs.ReadAllPressures()
	    try:
                ion_gauge_pressure = press[0]
                set_pressure(ion_gauge_pressure)
	    except:
		print "av"

class XGSSaver(threading.Thread):
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
		gauge_sql = "insert into pressure_NH3Synth_iongauge_massspec set time=\"" +  meas_time + "\", pressure = " + val
		print gauge_sql
		sqlInsert(gauge_sql)
		
				
quit = False
ion_gauge_pressure = 0

	
P = XGSClass()
PressSaver = XGSSaver()

P.start()
PressSaver.start()

while not quit:
	try:
		time.sleep(1)
		#print "Ion Gauge: " + "%.5g" % ion_gauge_pressure
		#print "Ion Pump: " +  "%.5g" % ion_pump_pressure
		#print "Turbo Temperature: " +  "%.5g" % turbo_pump_temp
	except:
		quit = True

