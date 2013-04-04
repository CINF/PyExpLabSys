import threading
import Queue
import time
from datetime import datetime
import MySQLdb
import omegabus


def sqlTime():
    sqltime = datetime.now().isoformat(' ')[0:19]
    return(sqltime)

def sqlInsert(query):
    try:
        cnxn = MySQLdb.connect(host="servcinf",user="gasmonitor",passwd="gasmonitor",db="cinfdata")
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


class omegaClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.omega = omegabus.OmegaBus()

    def run(self):
        global value_1
        global value_2
        global value_3
        global value_4
        while not quit:
            time.sleep(1)
            value_1 = self.omega.ReadValue(1)
            value_2 = self.omega.ReadValue(2)
            value_3 = self.omega.ReadValue(3)
            value_4 = self.omega.ReadValue(4)


class omegaSaver(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        while not quit:
            time.sleep(1)
            meas_time = sqlTime()
            val_1 = "%.2f" % value_1
            val_2 = "%.2f" % value_2
            val_3 = "%.2f" % value_3
            val_4 = "%.2f" % value_4

            ch01_sql = "insert into gasmonitor_ch01 set time=\"" +  meas_time + "\", value = " + val_1
            ch02_sql = "insert into gasmonitor_ch02 set time=\"" +  meas_time + "\", value = " + val_2
            ch03_sql = "insert into gasmonitor_ch03 set time=\"" +  meas_time + "\", value = " + val_3
            ch04_sql = "insert into gasmonitor_ch04 set time=\"" +  meas_time + "\", value = " + val_4
            print ch01_sql
            print ch02_sql
            print ch03_sql
            print ch04_sql
            sqlInsert(ch01_sql)
            sqlInsert(ch02_sql)
            sqlInsert(ch03_sql)
            sqlInsert(ch04_sql)
            time.sleep(60)
        
		
				
quit = False
value_1 = 0
value_2 = 0
value_3 = 0
value_4 = 0
	
O = omegaClass()
gasSaver = omegaSaver()

O.start()
gasSaver.start()

while not quit:
    try:
        time.sleep(1)
    except:
        quit = True

