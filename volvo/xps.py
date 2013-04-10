import sys
import time
import threading
import Queue
from datetime import datetime
import MySQLdb
import curses
import logging

sys.path.append('../')
import agilent_34972A as A
import SQL_saver

#TODO: These Non-class functions should be combined into a common module, as
#      they are used by other modules
def sqlTime():
    sqltime = datetime.now().isoformat(' ')[0:19]
    return(sqltime)

def sqlInsert(query, return_value=False):
    try:
        cnxn = MySQLdb.connect(host="servcinf",user="volvo",passwd="volvo",db="cinfdata")
	cursor = cnxn.cursor()
    except:
	print "Unable to connect to database"
	return()
    try:
	cursor.execute(query)
	cnxn.commit()

        if return_value: #TODO: AVOID HARD_CODED VALUES HERE!!!!!!!!
            query = "select id from measurements_dummy order by id desc limit 1"
            cursor.execute(query)
            id_number = cursor.fetchone()
            id_number = id_number[0]
        else:
            id_number = None

    except:
	print "SQL-error, query written below:"
	print query
        id_number = None

    cnxn.close()
    return(id_number)
    

def ReadNetwork(host, message):
    HOST, PORT = host, 9999
    data = message
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data + "\n", (HOST, PORT))
    received = sock.recv(1024)
    val = float(received)
    return(val)


#Dummy implementation of the sample-current reader
class SampleCurrent(threading.Thread):
    def __init__(self, table_id):
        threading.Thread.__init__(self)
        self.table_id = table_id

    def run():
        current = ReadNetwork('127.0.0.1', 'read_samplecurrent')
        print current
        time.sleep(5)

class XPS(threading.Thread):
    def __init__(self, hostname, anode, loglevel=logging.ERROR):
        threading.Thread.__init__(self)

        self.agilent = A.Agilent34972ADriver(address=hostname, method='lan')
	self.calib = 500 #Analyser voltage pr. input voltage
	self.meas_time = time.time()
        self.chamber_name = "dummy"
        self.table_id = -1
	if anode == 'Mg':
            self.x_ray = 1253.44
        if anode == 'Al':
            self.x_ray = 1487
        #TODO: Make an error if no correct anode is chosen

        #Clear log file
        with open('xps.txt', 'w'):
            pass
        logging.basicConfig(filename="xps.txt", level=logging.INFO)
        logging.info("Program started. Log level: " + str(loglevel))
        logging.basicConfig(level=logging.INFO)


    def create_table(self, masslabel, timestamp, comment):
        """ Create a new table for XPS data """
        #TODO: Add a bunch of meta-data to the insert statement
        query  = "insert into "
        query += "measurements_" + self.chamber_name
        query += " set type=2, time=\"" + timestamp + "\", " 
        query += "comment = \"" + comment + "\", mass_label=\"" + masslabel + "\""
        id_number = sqlInsert(query, True)

        return(id_number)

    def scan(self, start_energy, end_energy, step, queue=None):
        """ Perform a scan.
        If a queue is supplied, the data will be streamed continously into
        this queue, otherwise the data is printed to the console.
        """
        #TODO: Populate the queue with the data
        for binding_energy in range(end_energy,start_energy,-1 * step):
            kin_energy = str((self.x_ray - binding_energy)/self.calib)
	    if kin_energy > 0:
                 string = "SOURCE:VOLT " + kin_energy + ", (@205)"
            #TODO: Throw a proper error if the kinetic energy is negative
            self.agilent.scpi_comm(string)

            #TODO: Make the integration time configurable
	    time.sleep(0.25)

            count_string = self.agilent.scpi_comm("SENS:TOT:DATA? (@203)")
            count = int(float(count_string.strip()))
	    int_time = time.time() - self.meas_time
	    self.meas_time = time.time()

	    count_rate = count / int_time

            if queue == None:
                print binding_energy, count_rate
            else:
                query  = "insert into xy_values_" + self.chamber_name + " "
                query += "set measurement = " + str(self.table_id) + ", "
                query += "x=" + str(binding_energy) + ", "
                query += "y=" + str(count_rate)
                queue.put(query)



if __name__ == "__main__":
    timestamp = sqlTime()
    comment = 'Test-scan'

    sql_queue = Queue.Queue()

    sql_saver = SQL_saver.sql_saver(sql_queue, 'volvo')
    sql_saver.daemon = True
    sql_saver.start()

    xps = XPS('volvo-agilent-34972a','Mg')
    xps_id = xps.create_table('XPS data', timestamp, comment)
    current_id = xps.create_table('Sample current', timestamp, comment)
    xps.table_id = xps_id

    print xps_id
    print current_id

    xps.scan(1100,1300,1, sql_queue)

    time.sleep(1)

    print sql_queue.qsize()
