import threading
import Queue
import time
from datetime import datetime
import MySQLdb
import socket
import sys
sys.path.append('../')
import FindSerialPorts
import omegabus
import rosemount_nga2000 as nga
import omega_CNi32


def set_value(keyword,value):
    #print value
    HOST, PORT = "rasppi14", 9999
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
        for p in ports:
            AK = nga.AK_comm('/dev/' + p)
            id = AK.IdentifyDevice()
            if not (id == 'Error'):
                ports.remove(p)
                break
        print 'IR measurement: ' + p
        self.nga = AK

    def run(self):
        print self.nga.ReadConcentration()
        global ammonia_concentration
        global ammonia_raw_signal

        while not quit:
	    ammonia_concentration = self.nga.ReadConcentration()
            set_value('rosemount_calibrated',ammonia_concentration)
	    ammonia_raw_signal = self.nga.ReadUncorrelatedAnalogValue()
            set_value('rosemount_raw',ammonia_raw_signal)
            time.sleep(1)

class omegaClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        for p in ports:
            omega = omegabus.OmegaBus('/dev/' + p)
            try:
                omega.ReadSetup()
                ports.remove(p)
                break
            except:
                pass
        print 'Omegabus: ' + p
        self.omega = omega
        #self.omega = omegabus.OmegaBus()

    def run(self):
        global temp_1
        global temp_2
        global temp_3
        global temp_4
        while not quit:
            time.sleep(2)
            temp_1 = self.omega.ReadValue(1)
            set_value('temperature_1',temp_1)
            temp_2 = self.omega.ReadValue(2)
            set_value('temperature_2',temp_2)
            temp_3 = self.omega.ReadValue(3)
            set_value('temperature_3',temp_3)
            temp_4 = self.omega.ReadValue(4)
            set_value('temperature_4',temp_4)

class omegaCNClass(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        for p in ports:
            omegaCN = omega_CNi32.omega_comm('/dev/' + p)
            if omegaCN.ReadTemperature() > -9000:
                ports.remove(p)
                break
        print 'Omega CNi: ' + p
        self.omega_CN = omegaCN

    def run(self):
        global temp_5
        time.sleep(2)
        while True:
            try:
                time.sleep(3)
                temp_5 = float(self.omega_CN.ReadTemperature())
                #print temp_5
                set_value('temperature_5',temp_5)
            except:
                print sys.exc_info()[0]
                print sys.exc_info()[1]
                print sys.exc_info()[2]
                quit = True


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
                #print sql
		sqlInsert(sql)

		val = "%.9g" % ammonia_raw_signal
		sql = "insert into ir_nh3_raw_NH3Synth set time=\"" +  meas_time + "\", value = \"" + val + "\""
                #print sql
		sqlInsert(sql)

class omegaSaver(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.last_recorded_value_1 = -1
        self.last_recorded_value_2 = -1
        self.last_recorded_value_3 = -1
        self.last_recorded_value_4 = -1
        self.last_recorded_time = 1

    def run(self):
        while not quit:
            time.sleep(1)
            time_trigged = (time.time() - self.last_recorded_time) > 600
            val_trigged = not (self.last_recorded_value_1 - 3 < temp_1 < self.last_recorded_value_1 + 3 ) or not (self.last_recorded_value_2 - 3 < temp_2 < self.last_recorded_value_2 + 3) or not (self.last_recorded_value_3 - 3 < temp_3 < self.last_recorded_value_3 + 3) or not (self.last_recorded_value_4 - 3 < temp_4 < self.last_recorded_value_4 + 3)
            if (time_trigged or val_trigged):
                self.last_recorded_value_1 = temp_1
                self.last_recorded_value_2 = temp_2
                self.last_recorded_value_3 = temp_3
                self.last_recorded_value_4 = temp_4
                self.last_recorded_time = time.time()
                meas_time = sqlTime()
                val_temp_1 = "%.2f" % temp_1
                val_temp_2 = "%.2f" % temp_2
                val_temp_3 = "%.2f" % temp_3
                val_temp_4 = "%.2f" % temp_4
                temp_1_sql = "insert into temperature_NH3Synth set time=\"" +  meas_time + "\", temperature = " + val_temp_1
                temp_2_sql = "insert into temperature2_NH3Synth set time=\"" +  meas_time + "\", temperature = " + val_temp_2
                temp_3_sql = "insert into temperature3_NH3Synth set time=\"" +  meas_time + "\", temperature = " + val_temp_3
                temp_4_sql = "insert into temperature4_NH3Synth set time=\"" +  meas_time + "\", temperature = " + val_temp_4
                #print temp_1_sql
                #print temp_2_sql
                #print temp_3_sql
                #print temp_4_sql
                sqlInsert(temp_1_sql)
                sqlInsert(temp_2_sql)
                sqlInsert(temp_3_sql)
                sqlInsert(temp_4_sql)

class omegaCNSaver(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.last_recorded_value_5 = -1
        self.last_recorded_time = 1

    def run(self):
        while not quit:
            time.sleep(1)
            time_trigged = (time.time() - self.last_recorded_time) > 600
            val_trigged = not (self.last_recorded_value_5 - 1 < temp_5 < self.last_recorded_value_5 + 1 )
            if (time_trigged or val_trigged):
                self.last_recorded_value_5 = temp_5
                self.last_recorded_time = time.time()
                meas_time = sqlTime()
                val_temp_5 = "%.2f" % temp_5
                temp_5_sql = "insert into temperature5_NH3Synth set time=\"" +  meas_time + "\", temperature = " + val_temp_5
                #print temp_5_sql
                sqlInsert(temp_5_sql)


ports = FindSerialPorts.find_ports()
				
quit = False
ammonia_concentration = 0
ammonia_raw_signal = 0
temp_1 = 0
temp_2 = 0
temp_3 = 0
temp_4 = 0
temp_5 = 0

AK = AKclass()
AK_saver = AKSaver()

O = omegaClass()
tempSaver = omegaSaver()

OCN = omegaCNClass()
OCN.daemon = True
tempCNSaver = omegaCNSaver()

AK.start()
time.sleep(1)
AK_saver.start()

O.start()
tempSaver.start()

OCN.start()
tempCNSaver.start()

while not quit:
    try:
        time.sleep(1)
    except:
        quit = True

