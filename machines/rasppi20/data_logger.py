import threading
import Queue
import time
from datetime import datetime
import MySQLdb
import socket
import sys

def network_comm(host, port, string):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(10)
    sock.sendto(string + "\n", (host, port))
    received = sock.recv(1024)
    return received

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

class ChillerReader(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.chiller_temp = -9999
        self.chiller_flow = -9999
        self.chiller_temp_amb = -9999
        self.chiller_pressure = -9999
        self.chiller_temp_setpoint = -9999

    def run(self):
        while not quit:
            try:
                self.chiller_temp = network_comm('130.225.86.189', 9759, 'read_temperature')
                self.chiller_flow = network_comm('130.225.86.189', 9759, 'read_flow_rate')
                self.chiller_temp_amb = network_comm('130.225.86.189', 9759, 'read_ambient_temperature')
                self.chiller_pressure = network_comm('130.225.86.189', 9759, 'read_pressure')
                self.chiller_temp_setpoint = network_comm('130.225.86.189', 9759, 'read_setpoint')
                time.sleep(5)
            except:
                print 'Did not fetch values'


class ChillerSaver(threading.Thread):
    def __init__(self, reader):
        threading.Thread.__init__(self)
        self.last_recorded_time = 1
        self.reader = reader

    def run(self):
        while not quit:
            time.sleep(1)
            time_trigged = (time.time() - self.last_recorded_time) > 60
            if (time_trigged):
                self.last_recorded_time = time.time()
                meas_time = sqlTime()
                sql_pressure = "insert into chiller_stm312_pressure set time=\"" +  meas_time + "\", pressure = " + str(self.reader.chiller_pressure)
                sql_flow = "insert into chiller_stm312_flow set time=\"" +  meas_time + "\", flow = " + str(self.reader.chiller_flow)
                sql_temperature = "insert into chiller_stm312_temperature set time=\"" +  meas_time + "\", temperature = " + str(self.reader.chiller_temp)
                sql_temperature_amb = "insert into chiller_stm312_temperature_ambient set time=\"" +  meas_time + "\", temperature = " + str(self.reader.chiller_temp_amb)
                sql_temperature_setpoint = "insert into chiller_stm312_temperature_setpoint set time=\"" +  meas_time + "\", temperature = " + str(self.reader.chiller_temp_setpoint)
                chiller_status = network_comm('130.225.86.189', 9759, 'read_status')
                try:
                    if(chiller_status == 'On'):
                        print sql_pressure
                        sqlInsert(sql_pressure)
                        print sql_flow
                        sqlInsert(sql_flow)
                        print sql_temperature
                        sqlInsert(sql_temperature)
                        print sql_temperature_amb
                        sqlInsert(sql_temperature_amb)
                        print sql_temperature_setpoint
                        sqlInsert(sql_temperature_setpoint)
                    else:
                        print 'Chiller is off'
                except:
                    time.sleep(10)


if __name__ == '__main__':

    quit = False
    chiller_reader = ChillerReader()
    chiller_reader.start()

    time.sleep(5)

    chiller_saver = ChillerSaver(chiller_reader)
    chiller_saver.start()

    while not quit:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            quit = True

