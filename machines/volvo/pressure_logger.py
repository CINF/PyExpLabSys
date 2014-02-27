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
                gauge_sql = "insert into pressure_volvo set time=\"" + meas_time + "\", pressure = " + val
                print gauge_sql
                sqlInsert(gauge_sql)


quit = False
pressure = 0

P = XGSClass()
chambersaver = ChamberSaver()

P.start()
time.sleep(5)

chambersaver.start()



while not quit:
	try:
		time.sleep(1)
		#print "Ion Gauge: " + "%.5g" % ion_gauge_pressure
		#print "Ion Pump: " +  "%.5g" % ion_pump_pressure
		#print "Turbo Temperature: " +  "%.5g" % turbo_pump_temp
	except:
		quit = True

