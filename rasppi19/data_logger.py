import threading
import Queue
import time
from datetime import datetime
import MySQLdb
import socket
import serial

import omega_CNi32 as omega

import sys
sys.path.append('../')
import FindSerialPorts

def network_comm(host, port, string):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.1)
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

def OCSsqlInsert(query):
    try:
        cnxn = MySQLdb.connect(host="servcinf",user="oldclustersource",passwd="oldclustersource",db="cinfdata")
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

class STMReader(threading.Thread):
    def __init__(self, stm):
        threading.Thread.__init__(self)
        self.stm = stm
        self.stm_temp = -9999

    def run(self):
        while not quit:
            time.sleep(1)
            self.stm_temp = self.stm.ReadTemperature()
            #print self.stm_temp

class OCSReader(threading.Thread):
    def __init__(self, ocs):
        threading.Thread.__init__(self)
        self.ocs = ocs
        self.ocs_temp = -9999

    def run(self):
        while not quit:
            time.sleep(1)
            self.ocs_temp = self.ocs.ReadTemperature(address=2)
            #print self.stm_temp

class HPReader(threading.Thread):
    def __init__(self, hp):
        threading.Thread.__init__(self)
        self.hp = hp
        self.hp_temp = -9999

    def run(self):
        while not quit:
            #time.sleep(1)
            self.hp_temp = self.hp.ReadTemperature(address=1)
            if self.hp_temp >-998:
                try:
                    network_comm('rasppi19', 9990, 'set_hp_temp ' + str(self.hp_temp))
                except:
                    print 'Timeout'
            print self.hp_temp

class HighPressureTemperatureSaver(threading.Thread):
    def __init__(self, reader):
        threading.Thread.__init__(self)
        self.last_recorded_value = -1
        self.last_recorded_time = 1
        self.reader = reader

    def run(self):
        while not quit:
            time.sleep(1)
            time_trigged = (time.time() - self.last_recorded_time) > 600
            temp = self.reader.hp_temp
            val_trigged = not (self.last_recorded_value - 1 < temp < self.last_recorded_value + 1 )
            if (time_trigged or val_trigged):
                self.last_recorded_value = temp
                self.last_recorded_time = time.time()
                meas_time = sqlTime()
                val = "%.2f" % temp
                sql = "insert into temperature_stm312hp set time=\"" +  meas_time + "\", temperature = " + val
                print sql
                sqlInsert(sql)


class STMTemperatureSaver(threading.Thread):
    def __init__(self, reader):
        threading.Thread.__init__(self)
        self.last_recorded_value = -1
        self.last_recorded_time = 1
        self.reader = reader

    def run(self):
        while not quit:
            time.sleep(1)
            time_trigged = (time.time() - self.last_recorded_time) > 2
            temp = self.reader.stm_temp
            val_trigged = not (self.last_recorded_value - 2 < temp < self.last_recorded_value + 2 )
            if (time_trigged or val_trigged):
                self.last_recorded_value = temp
                self.last_recorded_time = time.time()
                meas_time = sqlTime()
                val = "%.2f" % temp
                sql = "insert into temperature_stm312_stm set time=\"" +  meas_time + "\", temperature = " + val
                print sql
                sqlInsert(sql)

class OCSTemperatureSaver(threading.Thread):
    def __init__(self, reader):
        threading.Thread.__init__(self)
        self.last_recorded_value = -1
        self.last_recorded_time = 1
        self.reader = reader

    def run(self):
        while not quit:
            time.sleep(1)
            time_trigged = (time.time() - self.last_recorded_time) > 600
            temp = self.reader.ocs_temp
            val_trigged = not (self.last_recorded_value - 2 < temp < self.last_recorded_value + 2 )
            if (time_trigged or val_trigged):
                self.last_recorded_value = temp
                self.last_recorded_time = time.time()
                meas_time = sqlTime()
                val = "%.2f" % temp
                sql = "insert into temperature_oldclustersource set time=\"" +  meas_time + "\", temperature = " + val
                print sql
                OCSsqlInsert(sql)


if __name__ == '__main__':
    """
    ports = FindSerialPorts.find_ports()
    for port in ports:
        print port
        try:
            tc_read = omega.omega_comm('/dev/' + port)
        except serial.serialutil.SerialException:
            continue
        id = tc_read.IdentifyDevice().strip()
        print id
        if id == '09':
            print 'High pressure cell: /dev/' + port
            hp = tc_read
        #if id == '09':
        #    print 'STM: /dev/' + port
        #    stm = tc_read
        #if id == '04':
        #    print 'OCS: /dev/' + port
        #    ocs = tc_read
    """
    tc_read = omega.omega_comm('/dev/ttyUSB0')


    quit = False
    hp_reader = HPReader(hp)
    hp_reader.start()

    #stm_reader = STMReader(stm)
    #stm_reader.start()

    ocs_reader = OCSReader(ocs)
    ocs_reader.start()
    
    time.sleep(5)

    hp_saver = HighPressureTemperatureSaver(hp_reader)
    hp_saver.start()

    #stm_saver = STMTemperatureSaver(stm_reader)
    #stm_saver.start()

    ocs_saver = OCSTemperatureSaver(ocs_reader)
    ocs_saver.start()
    
    while not quit:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            quit = True

