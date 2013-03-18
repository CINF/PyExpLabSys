import threading
import Queue
import time
from datetime import datetime
import MySQLdb
import xgs600
import omegabus
import socket

def set_value(keyword,value):
    print value
    HOST, PORT = "127.0.0.1", 9999
    data = "set_" + keyword +" " + str(value)
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
        cnxn = MySQLdb.connect(host="servcinf",user="uhvanneal",passwd="uhvanneal",db="cinfdata")
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
	    except:
		print "av"


class omegaClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.omega = omegabus.OmegaBus()

    def run(self):
        global temp_furnace_1
        global temp_furnace_2
        global temp_furnace_outside
        while not quit:
            time.sleep(2.5)
	    temp_furnace_outside = self.omega.ReadValue(1)
            set_value("temperature_outside",temp_furnace_outside)
	    temp_furnace_1 = self.omega.ReadValue(2)
            set_value("temperature_1",temp_furnace_1)
	    temp_furnace_2 = self.omega.ReadValue(3)
            set_value("temperature_2",temp_furnace_2)

	    
class XGSSaver(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
	self.last_recorded_value = -1
	self.last_recorded_time = 1
	
    def run(self):
	while not quit:
            time.sleep(1)
	    time_trigged = (time.time() - self.last_recorded_time) > 600
            val_trigged = not (self.last_recorded_value * 0.9 < ion_gauge_pressure < self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged) and ion_gauge_pressure > 0:
                self.last_recorded_value = ion_gauge_pressure
		self.last_recorded_time = time.time()
		meas_time = sqlTime()
		val = "%.5g" % ion_gauge_pressure
		gauge_sql = "insert into pressure_uhvanneal set time=\"" +  meas_time + "\", pressure = " + val
		print gauge_sql
		sqlInsert(gauge_sql)


class omegaSaver(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
	self.last_recorded_value_outside = -1
	self.last_recorded_value_1 = -1
	self.last_recorded_value_2 = -1
	self.last_recorded_time = 1
	
    def run(self):
	while not quit:
            time.sleep(1)
	    time_trigged = (time.time() - self.last_recorded_time) > 600
            val_trigged = not (self.last_recorded_value_outside - 3 < temp_furnace_outside < self.last_recorded_value_outside + 3 or self.last_recorded_value_1 - 3 < temp_furnace_1 < self.last_recorded_value_1 + 3 or self.last_recorded_value_2 - 3 < temp_furnace_2 < self.last_recorded_value_2 + 3)
            if (time_trigged or val_trigged) and temp_furnace_outside > 0:
                self.last_recorded_value_outside = temp_furnace_outside
                self.last_recorded_value_1 = temp_furnace_1
                self.last_recorded_value_2 = temp_furnace_2
		self.last_recorded_time = time.time()
		meas_time = sqlTime()
		val_temp_outside = "%.2f" % temp_furnace_outside
		val_temp_1 = "%.2f" % temp_furnace_1
		val_temp_2 = "%.2f" % temp_furnace_2
		temp_outside_sql = "insert into temperature_uhvanneal_outside set time=\"" +  meas_time + "\", temperature = " + val_temp_outside
		temp_1_sql = "insert into temperature_uhvanneal_1 set time=\"" +  meas_time + "\", temperature = " + val_temp_1
		temp_2_sql = "insert into temperature_uhvanneal_2 set time=\"" +  meas_time + "\", temperature = " + val_temp_2
		print temp_outside_sql
		print temp_1_sql
		print temp_2_sql
		sqlInsert(temp_outside_sql)
		sqlInsert(temp_1_sql)
		sqlInsert(temp_2_sql)

				
quit = False
ion_gauge_pressure = 0
temp_furnace_outside = 0
temp_furnace_1 = 0
temp_furnace_2 = 0

	
P = XGSClass()
PressSaver = XGSSaver()

O = omegaClass()
tempSaver = omegaSaver()

P.start()
PressSaver.start()

O.start()
tempSaver.start()

while not quit:
	try:
		time.sleep(1)
		#print "Ion Gauge: " + "%.5g" % ion_gauge_pressure
		#print "Ion Pump: " +  "%.5g" % ion_pump_pressure
		#print "Turbo Temperature: " +  "%.5g" % turbo_pump_temp
	except:
		quit = True
