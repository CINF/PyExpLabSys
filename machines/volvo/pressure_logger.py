import threading
import time
from datetime import datetime
import MySQLdb
import xgs600
import socket
import agilent_34972A

def set_pressure(value):
    HOST, PORT = "130.225.87.86", 9999
    data = "set_pressure " + str(value)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data + "\n", (HOST, PORT))
    received = sock.recv(1024)
    return_val = False
    if received == "ok":
        return_val = True
    return return_val

def set_temperature(value):
    HOST, PORT = "130.225.87.86", 9999
    data = "set_temperature " + str(value)
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
        cnxn = MySQLdb.connect(host="servcinf",user="volvo",passwd="volvo",db="cinfdata")
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


class MuxClass(threading.Thread):
    """ Temperature reader """
    def __init__(self):
        threading.Thread.__init__(self)
        self.mux = agilent_34972A.Agilent34972ADriver('volvo-agilent-34972a')

    def run(self):
        global temperature
        while not quit:
            time.sleep(2)
            mux_list = self.mux.read_single_scan()
            #print mux_list
	    try:
                temperature = mux_list[0]
	    except:
		print "av"


class XGSClass(threading.Thread):
    """ Pressure reader """
    def __init__(self):
        threading.Thread.__init__(self)
        self.xgs = xgs600.XGS600Driver()

    def run(self):
        global pressure
        while not quit:
            time.sleep(2.5)
            press = self.xgs.read_all_pressures()
	    try:
                pressure = press[0]
	    except:
		print "av"


class ChamberSaver(threading.Thread):
    """Save the main chamber pressure """
    def __init__(self):
        threading.Thread.__init__(self)
        self.last_recorded_value = -1
        self.last_recorded_time = 1

    def run(self):
        while not quit:
            time.sleep(1)
            time_trigged = (time.time() - self.last_recorded_time) > 60
            val_trigged = not (self.last_recorded_value * 0.9 < pressure < self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged) and pressure > 0:
                self.last_recorded_value = pressure
                self.last_recorded_time = time.time()
                meas_time = sqlTime()
                val = "%.5g" % pressure
                set_pressure(pressure)
                gauge_sql = "insert into dateplots_volvo set type=21, time=\"" + meas_time + "\", value = " + val
                print gauge_sql
                sqlInsert(gauge_sql)

class TemperatureSaver(threading.Thread):
    """Save the main chamber pressure """
    def __init__(self):
        threading.Thread.__init__(self)
        self.last_recorded_value = -1
        self.last_recorded_time = 1

    def run(self):
        while not quit:
            time.sleep(1)
            time_trigged = (time.time() - self.last_recorded_time) > 60
            val_trigged = not (self.last_recorded_value * 0.9 < temperature < self.last_recorded_value * 1.1)
            if (time_trigged or val_trigged) and pressure > 0:
                set_temperature(temperature)
                self.last_recorded_value = temperature
                self.last_recorded_time = time.time()
                meas_time = sqlTime()
                val = "%.5g" % temperature
                #set_temperature(temperature)
                temp_sql = "insert into dateplots_volvo set type=20, time=\"" + meas_time + "\", value = " + val
                print temp_sql
                sqlInsert(temp_sql)



quit = False
pressure = 0
temperature = 0

P = XGSClass()
M = MuxClass()
chambersaver = ChamberSaver()

temperaturesaver = TemperatureSaver()

P.start()
M.start()
time.sleep(5)

chambersaver.start()
temperaturesaver.start()


while not quit:
	try:
		time.sleep(1)
		#print "Ion Gauge: " + "%.5g" % ion_gauge_pressure
		#print "Ion Pump: " +  "%.5g" % ion_pump_pressure
		#print "Turbo Temperature: " +  "%.5g" % turbo_pump_temp
	except:
		quit = True

