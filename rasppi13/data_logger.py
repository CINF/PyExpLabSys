import threading
import Queue
import time
from datetime import datetime
import MySQLdb
import socket

def sqlTime():
    sqltime = datetime.now().isoformat(' ')[0:19]
    return(sqltime)

def sqlInsert(query):
    try:
        cnxn = MySQLdb.connect(host="servcinf",user="stm312",passwd="stm312",db="cinfdata")
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

class reader_class(threading.Thread):
    def __init__(self, udp_string):
        threading.Thread.__init__(self)
        self.value = -1
        self.udp_string = udp_string

    def read(self):
        HOST, PORT = 'rasppi13', 9999
        data = self.udp_string
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        sock.sendto(data + "\n", (HOST, PORT))
        received = sock.recv(1024)
        try:
            value = float(received)
        except:
            value = -1
        return value

    def run(self):
        while not quit:
            time.sleep(2.5)
            self.value = self.read()

	    try:
                self.value = self.read()
	    except:
		print "av - pirani"

class pirani_saver(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
	self.last_recorded_value = -1
	self.last_recorded_time = 1
	
    def run(self):
	while not quit:
            value = pirani_reader.value
            print "Pirani: " + str(value)
            time.sleep(1)
	    time_trigged = (time.time() - self.last_recorded_time) > 30
            val_trigged = (value>0) and (not (self.last_recorded_value * 0.9 < value < self.last_recorded_value * 1.1))
            if (time_trigged or val_trigged) and (value > -0.1):
                self.last_recorded_value = value
		self.last_recorded_time = time.time()
		meas_time = sqlTime()
		val = "%.5g" % value
		gauge_sql = "insert into pressure_stm312hp_pirani set time=\"" +  meas_time + "\", pressure = " + val
		print gauge_sql
		sqlInsert(gauge_sql)

class pc_saver(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
	self.last_recorded_value = -1
	self.last_recorded_time = 1
	
    def run(self):
	while not quit:
            value = pc_reader.value
            print "Pressure controller: " + str(value)
            time.sleep(1)
	    time_trigged = (time.time() - self.last_recorded_time) > 600
            val_trigged = not (self.last_recorded_value * 0.9 < value < self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged) and (value > 0):
                self.last_recorded_value = value
		self.last_recorded_time = time.time()
		meas_time = sqlTime()
		val = "%.5g" % value
		gauge_sql = "insert into pressure_stm312hp_pressure_controller set time=\"" +  meas_time + "\", pressure = " + val
		print gauge_sql
		sqlInsert(gauge_sql)
		
				
quit = False
pirani_reader = reader_class('read_pirani')
pc_reader = reader_class('read_pressure')
pirani_reader.start()
pc_reader.start()
	
Pirani = pirani_saver()
Pirani.start()
PC = pc_saver()
PC.start()

while not quit:
	try:
		time.sleep(1)
		#print "Ion Gauge: " + "%.5g" % ion_gauge_pressure
		#print "Ion Pump: " +  "%.5g" % ion_pump_pressure
		#print "Turbo Temperature: " +  "%.5g" % turbo_pump_temp
	except:
		quit = True

