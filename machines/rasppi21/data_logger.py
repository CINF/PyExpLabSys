import threading
import Queue
import time
from datetime import datetime
import MySQLdb
import socket
import sys

import sql_credentials as credentials

sys.path.append('../')
import FindSerialPorts
import InficonSQM160 as qcm
import polyscience_4100

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
        cnxn = MySQLdb.connect(host="servcinf", user=credentials.username, passwd=credentials.password, db="cinfdata")
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

class QcmReader(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        for port in ports:
            try:
                inficon = qcm.InficonSQM160('/dev/' + port)
                inficon.show_version()
                print 'QCM: ' + port
                break
            except IndexError:
                pass
        ports.remove(port)
        self.inficon = inficon
        self.frequency = -1
        self.lifetime = -1
        self.thickness = -1

    def run(self):
        while not quit:
            self.frequency = self.inficon.frequency()
            self.crystal_life = self.inficon.crystal_life()
            self.thickness =  self.inficon.thickness()
            time.sleep(5)


class QcmSaver(threading.Thread):
    def __init__(self, reader):
        threading.Thread.__init__(self)
        self.last_recorded_time = 1
        self.reader = reader

    def run(self):
        while not quit:
            time.sleep(1)
            time_trigged = (time.time() - self.last_recorded_time) > 200
            if (time_trigged):
                self.last_recorded_time = time.time()
                meas_time = sqlTime()
                sql_thickness = "insert into sputterchamber_qcm_thickness set time=\"" +  meas_time + "\", value = " + str(self.reader.thickness)
                sql_crystal_life = "insert into sputterchamber_qcm_crystal_life set time=\"" +  meas_time + "\", value = " + str(self.reader.crystal_life)
                sql_frequency = "insert into sputterchamber_qcm_frequency set time=\"" +  meas_time + "\", value = " + str(self.reader.frequency)
                print sql_frequency

                sqlInsert(sql_thickness)
                sqlInsert(sql_crystal_life)
                sqlInsert(sql_frequency)
                time.sleep(10)

class ChillerReader(threading.Thread):
    def __init__(self):
        for port in ports:
            chiller = polyscience_4100.Polyscience_4100('/dev/' + port)
            if not (chiller.read_status() == 'error'):
                print 'Chiller: ' + port
                self.chiller = chiller
                ports.remove(port)
                break

        threading.Thread.__init__(self)
        self.temp = -9999
        self.flow = -9999
        self.temp_amb = -9999
        self.pressure = -9999
        self.temp_setpoint = -9999
        self.status = 'Off'

    def run(self):
        while not quit:
             #self.chiller_temp = network_comm('130.225.86.120', 9759, 'read_temperature')
            self.temp = self.chiller.read_temperature()
            self.flow = self.chiller.read_flow_rate()
            self.temp_amb = self.chiller.read_ambient_temperature()
            self.pressure = self.chiller.read_pressure()
            self.temp_setpoint = self.chiller.read_setpoint()
            self.status = self.chiller.read_status()
            time.sleep(5)

class ChillerSaver(threading.Thread):
    def __init__(self, reader):
        threading.Thread.__init__(self)
        self.last_recorded_time = 1
        self.reader = reader

    def run(self):
        while not quit:
            time.sleep(1)
            time_trigged = (time.time() - self.last_recorded_time) > 200
            if (time_trigged):
                self.last_recorded_time = time.time()
                meas_time = sqlTime()
                sql_pressure = "insert into chiller_sputterchamber_pressure set time=\"" +  meas_time + "\", pressure = " + str(self.reader.pressure)
                sql_flow = "insert into chiller_sputterchamber_flow set time=\"" +  meas_time + "\", flow = " + str(self.reader.flow)
                sql_temperature = "insert into chiller_sputterchamber_temperature set time=\"" +  meas_time + "\", temperature = " + str(self.reader.temp)
                sql_temperature_amb = "insert into chiller_sputterchamber_temperature_ambient set time=\"" +  meas_time + "\", temperature = " + str(self.reader.temp_amb)
                sql_temperature_setpoint = "insert into chiller_sputterchamber_temperature_setpoint set time=\"" +  meas_time + "\", temperature = " + str(self.reader.temp_setpoint)
                #chiller_status = network_comm('130.225.86.120', 9759, 'read_status')
                try:
                    if(self.reader.status == 'On'):
                        #print sql_pressure
                        sqlInsert(sql_pressure)
                        #print sql_flow
                        sqlInsert(sql_flow)
                        #print sql_temperature
                        sqlInsert(sql_temperature)
                        #print sql_temperature_amb
                        sqlInsert(sql_temperature_amb)
                        #print sql_temperature_setpoint
                        sqlInsert(sql_temperature_setpoint)
                    else:
                        print 'Chiller is off'
                except:
                    time.sleep(10)


if __name__ == '__main__':
    ports = FindSerialPorts.find_ports()

    quit = False
    chiller_reader = ChillerReader()
    time.sleep(2)
    qcm_reader = QcmReader()
    time.sleep(2)

    chiller_reader.start()
    qcm_reader.start()
    
    time.sleep(5)

    chiller_saver = ChillerSaver(chiller_reader)
    chiller_saver.start()

    qcm_saver = QcmSaver(qcm_reader)
    qcm_saver.start()

    while not quit:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            quit = True

