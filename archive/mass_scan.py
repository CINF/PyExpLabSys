import sys
import time
import threading
import Queue
from datetime import datetime
import MySQLdb
import curses
import logging
import numpy as np

import agilent_34972A as A
import SQL_saver

#TODO: These Non-class functions should be combined into a common module, as
#      they are used by other modules
def sqlTime():
    sqltime = datetime.now().isoformat(' ')[0:19]
    return(sqltime)

def sqlInsert(query, return_value=False, chamber='dummy'):
    try:
        cnxn = MySQLdb.connect(host="servcinf",user="tof",passwd="tof",db="cinfdata")
	cursor = cnxn.cursor()
    except:
	print "Unable to connect to database"
	return()
    try:
	cursor.execute(query)
	cnxn.commit()

        if return_value:
            query = "select id from measurements_" + chamber + " order by id desc limit 1"
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
    
class MassScan(threading.Thread):
    def __init__(self, hostname, loglevel=logging.ERROR):
        threading.Thread.__init__(self)

        self.agilent = A.Agilent34972ADriver(name=hostname)
	self.calib = 299.3 #Mass-value for 10V input
	self.meas_time = time.time()
        self.chamber_name = "tof"
        self.table_id = -1

        #Clear log file
        with open('massscan.txt', 'w'):
            pass
        logging.basicConfig(filename="massscan.txt", level=logging.INFO)
        logging.info("Program started. Log level: " + str(loglevel))
        logging.basicConfig(level=logging.INFO)


    def create_table(self, masslabel, timestamp, comment):
        """ Create a new table for mass-scan data """
        #TODO: Add a bunch of meta-data to the insert statement
        query  = "insert into "
        query += "measurements_" + self.chamber_name
        query += " set type=4, time=\"" + timestamp + "\", " 
        query += "comment = \"" + comment + "\", mass_label=\"" + masslabel + "\""
        id_number = sqlInsert(query, True, chamber=self.chamber_name)
        return(id_number)

    def scan(self, start, end, step=0.1, queue=None):
        """ Perform a scan.
        If a queue is supplied, the data will be streamed continously into
        this queue, otherwise the data is printed to the console.
        """
        step = step*1.0
        #TODO: Populate the queue with the data
        self.agilent.set_scan_list(['120'])
        for mass in np.arange(start, end, step):
            voltage = str(10 * mass / self.calib)
            string = "SOURCE:VOLT " + voltage + ", (@205)"
            self.agilent.scpi_comm(string)
            value = -1 * self.agilent.read_single_scan()[0]

            if queue == None:
                print binding_energy, count_rate
            else:
                query  = "insert into xy_values_" + self.chamber_name + " "
                query += "set measurement = " + str(self.table_id) + ", "
                query += "x=" + str(mass) + ", "
                query += "y=" + str(value)
                queue.put(query)


if __name__ == "__main__":
    timestamp = sqlTime()
    comment = 'Cold ion-pump'

    sql_queue = Queue.Queue()

    sql_saver = SQL_saver.sql_saver(sql_queue, 'tof')
    sql_saver.daemon = True
    sql_saver.start()

    massscan = MassScan('tof-agilent-34972a')
    ms_id = massscan.create_table('Mass Scan', timestamp, comment)
    massscan.table_id = ms_id

    print ms_id

    massscan.scan(0,50,0.05, sql_queue)

    time.sleep(1)

    print sql_queue.qsize()
