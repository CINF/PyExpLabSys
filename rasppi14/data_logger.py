import threading
import Queue
import time
from datetime import datetime
import MySQLdb
import rosemount_nga2000 as nga
import omegabus


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

class AKclass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.nga = nga.AK_comm('/dev/ttyUSB0')

    def run(self):
        global ammonia_concentration
        global ammonia_raw_signal
        while not quit:
	    ammonia_concentration = self.nga.ReadConcentration()
	    ammonia_raw_signal = self.nga.ReadUncorrelatedAnalogValue()
            time.sleep(1)

class omegaClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.omega = omegabus.OmegaBus()

    def run(self):
        global temp_1
        global temp_2
        while not quit:
            time.sleep(1)
            temp_1 = self.omega.ReadValue(1)
            temp_2 = self.omega.ReadValue(2)



class AKSaver(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
	self.last_recorded_value = -1
	self.last_recorded_time = 1
	
    def run(self):
	while not quit:
            time.sleep(1)
	    time_trigged = (time.time() - self.last_recorded_time) > 5
            #val_trigged = not (self.last_recorded_value * 0.9 < ammonia_concentration < self.last_recorded_value * 1.1)
            val_trigged = False #For the time being, we simply record for every 20s
            if (time_trigged or val_trigged):
                self.last_recorded_value = ammonia_concentration
		self.last_recorded_time = time.time()
		meas_time = sqlTime()
		val = "%.7g" % ammonia_concentration
		sql = "insert into ir_nh3_concentration_NH3Synth set time=\"" +  meas_time + "\", concentration = \"" + val + "\""
                print sql
		sqlInsert(sql)

		val = "%.9g" % ammonia_raw_signal
		sql = "insert into ir_nh3_raw_NH3Synth set time=\"" +  meas_time + "\", value = \"" + val + "\""
                print sql
		sqlInsert(sql)

class omegaSaver(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.last_recorded_value_1 = -1
        self.last_recorded_value_2 = -1
        self.last_recorded_time = 1

    def run(self):
        while not quit:
            time.sleep(1)
            time_trigged = (time.time() - self.last_recorded_time) > 600
            val_trigged = not (self.last_recorded_value_1 - 3 < temp_1 < self.last_recorded_value_1 + 3 ) or not (self.last_recorded_value_2 - 3 < temp_2 < self.last_recorded_value_2 + 3)
            if (time_trigged or val_trigged):
                self.last_recorded_value_1 = temp_1
                self.last_recorded_value_2 = temp_2
                self.last_recorded_time = time.time()
                meas_time = sqlTime()
                val_temp_1 = "%.2f" % temp_1
                val_temp_2 = "%.2f" % temp_2
                temp_1_sql = "insert into temperature_NH3Synth set time=\"" +  meas_time + "\", temperature = " + val_temp_1
                temp_2_sql = "insert into temperature2_NH3Synth set time=\"" +  meas_time + "\", temperature = " + val_temp_2
                print temp_1_sql
                print temp_2_sql
                sqlInsert(temp_1_sql)
                sqlInsert(temp_2_sql)
		
				
quit = False
ammonia_concentration = 0
ammonia_raw_signal = 0
temp_1 = 0
temp_2 = 0
	
AK = AKclass()
AK_saver = AKSaver()

O = omegaClass()
tempSaver = omegaSaver()

AK.start()
time.sleep(1)
AK_saver.start()

O.start()
tempSaver.start()

while not quit:
    try:
        time.sleep(1)
    except:
        quit = True

