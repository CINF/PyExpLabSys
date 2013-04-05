import sys
import time
import threading
import Queue
from datetime import datetime
import MySQLdb

sys.path.append('../')
import agilent_34972A as A

def sqlTime():
    sqltime = datetime.now().isoformat(' ')[0:19]
    return(sqltime)

class XPS():
    def __init__(self, hostname, anode):
        self.agilent = A.Agilent34972ADriver(address=hostname, method='lan')
	self.calib = 500 #Analyser voltage pr. input voltage
	self.meas_time = time.time()
        self.measuement_id = -1
        self.table_name = "measurements_dummy"
	if anode == 'Mg':
            self.x_ray = 1253.44
        if anode == 'Al':
            self.x_ray = 1487
        #TODO: Make an error if no correct anode is chosen

    def create_table(self, timestamp, comment):
        """ Create a new table for XPS data """
        #TODO: Add a bunch of meta-data to the insert statement
        query  = "insert into "
        query += self.table_name
        query += " set type=2, timestamp=" + timestamp + ", comment = \"" + comment + "\""
        #execute mysql
	#Get id
        self.measurement_id = -1
	return True #Return False if something went wrong

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
	    time.sleep(1)

            count_string = self.agilent.scpi_comm("SENS:TOT:DATA? (@203)")
            count = int(float(count_string.strip()))
	    int_time = time.time() - self.meas_time
	    self.meas_time = time.time()

	    count_rate = count / int_time
            print binding_energy, count_rate



if __name__ == "__main__":
    xps = XPS('volvo-agilent-34972a','Mg')
    xps.scan(1295,1300,1)
