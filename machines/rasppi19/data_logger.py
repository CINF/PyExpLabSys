""" Logging and measuring of temperatures with omega
the script is working with stm312 and the oldcluster source
making it unnesesary complicated as the two chambers have very
different mysql stryctures"""
import threading
import time
from datetime import datetime
import MySQLdb
import PyExpLabSys.drivers.omega_cni as omega
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.loggers import ContinuousLogger
import credentials

def sqlTime():
    sqltime = datetime.now().isoformat(' ')[0:19]
    return(sqltime)

def OCSsqlInsert(query):
    """sql function for old cluster source
    until it is moved to the new DB structure"""
    try:
        cnxn = MySQLdb.connect(host="servcinf",
                               user="oldclustersource",
                               passwd="oldclustersource",
                               db="cinfdata")
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


class Reader(threading.Thread):
    def __init__(self, omega, pullsocket):
        threading.Thread.__init__(self)
        self.omega = omega
        self.pullsocket = pullsocket
        self.hp_temp = -9999
        self.ocs_temp = -9999

    def run(self):
        while not quit:
            time.sleep(1)
            hp_temp = self.omega.read_temperature(address=1)
            ocs_temp = self.omega.read_temperature(address=2)
            if ocs_temp > -998:
                self.ocs_temp = ocs_temp
            if hp_temp > -998:
                self.hp_temp = hp_temp
            if self.hp_temp > -998:
                try:
                    self.pullsocket.set_point_now('stm312_hpc_temperature', self.hp_temp)
                except:
                    print 'Timeout'


class HighPressureTemperatureSaver(threading.Thread):
    def __init__(self, reader, db_logger):
        threading.Thread.__init__(self)
        self.last_recorded_value = -1
        self.last_recorded_time = 1
        self.reader = reader
        self.db_logger = db_logger

    def run(self):
        while not quit:
            time.sleep(1)
            time_trigged = (time.time() - self.last_recorded_time) > 600
            temp = self.reader.hp_temp
            print "Temperature: "  + str(temp)
            print "Last recorded temp: " + str(self.last_recorded_value)
            val_trigged = not (self.last_recorded_value - 1 < temp < self.last_recorded_value + 1 )
            if (time_trigged or val_trigged):
                print '!!!!!!!!!!!!!'
                self.last_recorded_value = temp
                self.last_recorded_time = time.time()
                self.db_logger.enqueue_point_now('stm312_hpc_temperature', temp)
                print(temp)


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
    quit = False
    pullsocket = DateDataPullSocket('stm312 hptemp',
                                    ['stm312_hp_temperature'],
                                    timeouts=[4.0])
    pullsocket.start()
    db_logger = ContinuousLogger(table='dateplots_stm312',
                                 username=credentials.user,
                                 password=credentials.passwd,
                                 measurement_codenames=['stm312_hpc_temperature'])
    db_logger.start()
    tc_reader = omega.ISeries('/dev/ttyUSB0',
                              9600,
                              comm_stnd='rs485')
    temperature_reader = Reader(tc_reader, pullsocket)
    temperature_reader.start()

    time.sleep(5)

    hp_saver = HighPressureTemperatureSaver(temperature_reader, db_logger)
    hp_saver.start()

    #stm_saver = STMTemperatureSaver(stm_reader)
    #stm_saver.start()

    ocs_saver = OCSTemperatureSaver(temperature_reader)
    ocs_saver.start()
    
    while not quit:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            quit = True
