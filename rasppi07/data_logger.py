import threading
import Queue
import time
from datetime import datetime
import MySQLdb
import sys
sys.path.append('../')
import rosemount_nga2000 as nga


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
            time.sleep(2)


class AKSaver(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
	self.last_recorded_value = -1
	self.last_recorded_time = 1
	
    def run(self):
	while not quit:
            time.sleep(1)
	    time_trigged = (time.time() - self.last_recorded_time) > 20
            #val_trigged = not (self.last_recorded_value * 0.9 < ammonia_concentration < self.last_recorded_value * 1.1)
            val_trigged = False #For the time being, we simply record for every 20s
            if (time_trigged or val_trigged):
                self.last_recorded_value = ammonia_concentration
		self.last_recorded_time = time.time()
		meas_time = sqlTime()
		val = "%.5g" % ammonia_concentration
		sql = "insert into ir_nh3_concentration_NH3Synth set time=\"" +  meas_time + "\", concentration = \"" + val + "\""
                print sql
		sqlInsert(sql)

		val = "%.5g" % ammonia_raw_signal
		sql = "insert into ir_nh3_raw_NH3Synth set time=\"" +  meas_time + "\", value = \"" + val + "\""
                print sql
		sqlInsert(sql)
		
				
quit = False
ammonia_concentration = 0
ammonia_raw_signal = 0

	
AK = AKclass()
AK_saver = AKSaver()

AK.start()
time.sleep(1)
AK_saver.start()

while not quit:
    try:
        time.sleep(1)
    except:
        quit = True

