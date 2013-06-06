import threading
import Queue
import serial
import time
#import matplotlib.pyplot as plt
import MySQLdb
import curses
import logging
import socket

import sys
sys.path.append('../')
import SQL_saver

import qmg_status_output
import qmg_meta_channels


class QMG422():

    def __init__(self, sqlqueue=None, loglevel=logging.ERROR):
        self.f = serial.Serial('/dev/ttyUSB0',19200)
        if not sqlqueue == None:
            self.sqlqueue = sqlqueue
        else: #We make a dummy queue to make the program work
            self.sqlqueue = Queue.Queue()
        self.operating_mode = "Idling"
        self.current_timestamp = "None"
        self.measurement_runtime = 0
        self.stop = False
        self.chamber = 'dummy'
        self.channel_list = {}
        
        #Clear log file
        with open('qms.txt', 'w'):
            pass
        logging.basicConfig(filename="qms.txt", level=logging.INFO)
        logging.info("Program started. Log level: " + str(loglevel))
        logging.basicConfig(level=logging.INFO)
        
    def comm(self,command,debug=False):
        """ Communicates with Baltzers/Pferiffer Mass Spectrometer
        
        Implements the low-level protocol for RS-232 communication with the
        instrument. High-level protocol can be implemented using this as a
        helper
        
        """
        t = time.time()
        logging.debug("Command in progress: " + command)

        n = self.f.inWaiting()
        if n>0: #Skip characters that are currently waiting in line
            debug_info = self.f.read(n)
            logging.debug("Elements not read: " + str(n) + 
                          ": Contains: " + debug_info)
            
        ret = " "
        error_counter = 0
        while not ret[0] == chr(6):
            error_counter += 1
            self.f.write(command + '\r')
            ret = self.f.readline()

            logging.debug("Debug: Error counter: " + str(error_counter))
            logging.debug("Debug! In waiting: " + str(n))

            if error_counter > 3:
                logging.warning("Communication error: " + str(error_counter))
            if error_counter > 10:
                logging.error("Communication error: " + str(error_counter))
            if error_counter > 50:
                logging.error("Communication error! Quit program!")
                quit()
                
        #We are now quite sure the instrument is ready to give back data        
        self.f.write(chr(5))
        ret = self.f.readline()

        logging.debug("Number in waiting after enq: " + str(n))
        logging.debug("Return value after enq:" + ret)
        logging.debug("Ascii value of last char in ret: " + str(ord(ret[-1])))
        
        if (ret[-1] == chr(10)) or (ret[-1] == chr(13)):
            ret_string = ret.strip()
        else:
            logging.info("Wrong line termination")
            self.f.write(chr(5))
            time.sleep(0.05)
            n = self.f.inWaiting()
            ret = self.f.read(n)

        return ret_string

    def communication_mode(self, computer_control=False):
        """ Returns and sets the communication mode """
        if computer_control:
            ret_string = self.comm('CMO ,1')
        else:
            ret_string = self.comm('CMO')
        comm_mode = ret_string

        if ret_string == '0':
            comm_mode = 'Console Keybord'
        if ret_string == '1':
            comm_mode = 'ASCII'
        if ret_string == '2':
            comm_mode = 'BIN'
        if ret_string == '3':
            comm_mode = 'Modem'
        if ret_string == '4':
            comm_mode = 'LAN'
        return comm_mode

    def emission_status(self, current=-1, turn_off=False, turn_on=False):
        """ Get or set the emission status. """
        if current>-1:
            ret_string = self.comm('EMI ,' + str(current))
        else:
            ret_string = self.comm('EMI')
        emission_current = float(ret_string.strip())
 
        if turn_off ^ turn_on:
            if turn_off:
                self.comm('FIE ,0')
            if turn_on:
                self.comm('FIE ,1')
        ret_string = self.comm('FIE')

        filament_on = ret_string == '1'
        return emission_current,filament_on

    def sem_status(self, voltage=-1, turn_off=False, turn_on=False):
        """ Get or set the SEM status """
        if voltage>-1:
            ret_string = self.comm('SHV ,' + str(voltage))
        else:
            ret_string = self.comm('SHV')
        sem_voltage = int(ret_string)


        if turn_off ^ turn_on: #Only accept self-consistent sem-changes
            if turn_off:
                self.comm('SEM ,0')
            if turn_on:
                self.comm('SEM ,1')
        ret_string = self.comm('SEM')
        sem_on = ret_string == "1"
        
        return sem_voltage, sem_on

    def detector_status(self, SEM=False, faraday_cup=False):
        """ Choose between SEM and Faraday cup measurements"""
        if SEM ^ faraday_cup:
            if SEM:
                ret_string = self.comm('SDT ,1')
            if faraday_cup:
                ret_string = self.comm('SDT ,0')
        else:
            ret_string = self.comm('SDT')
        
        if int(ret_string) > 0:
            detector = "SEM"
        else:
            detector = "Faraday Cup"
        
        return detector

    def read_voltages(self):
        """ Print all MS voltages """
        print "V01: " + self.comm('VO1') #0..150,   1V steps
        print "V02: " + self.comm('VO2') #0..125,   0.5V steps
        print "V03: " + self.comm('VO3') #-30..30,  0.25V steps
        print "V04: " + self.comm('VO4') #0..60,    0.25V steps
        print "V05: " + self.comm('VO5') #0..450,   2V steps
        print "V06: " + self.comm('VO6') #0..450,   2V steps
        print "V07: " + self.comm('VO7') #0..250,   1V steps
        print "V08: " + self.comm('VO8') #-125..125,1V steps 
        print "V09: " + self.comm('VO9') #0..60    ,0.25V steps

    def simulation(self):
        """ Chekcs wheter the instruments returns real or simulated data """
        ret_string = self.comm('TSI ,0')
        if int(ret_string) == 0:
            sim_state = "Simulation not running"
        else:
            sim_state = "Simulation running"
        return sim_state

    def qms_status(self):
        """ Returns a string with the current status of the instrument """
        ret_string = self.comm('ESQ')
        n = ret_string.find(',')

        sn = int(ret_string[0:n]) #status_number
        st = "" #Status txt

        st += 'Cycle ' + ('Run' if (sn % 2) == 1 else 'Halt')
        sn = sn/2
        st = st + '\n' + ('Multi' if (sn % 2) == 1 else 'Mono')
        sn = sn/2
        st = st + '\n' + 'Emission ' + ('on' if (sn % 2) == 1 else 'off')
        sn = sn/2
        st += '\nSEM ' + ('on' if (sn % 2) == 1 else 'off')
        sn = sn/2
        #The rest of the status bits is not currently used
        return st

    def config_channel(self, channel, mass=-1, speed=-1, enable=""):
        """ Config a MS channel for measurement """
        self.comm('SPC ,' + str(channel)) #SPC: Select current parameter channel
        
        if mass>-1:
            self.comm('MFM ,' + str(mass))
            
        if speed>-1:
            self.comm('MSD ,' + str(speed))
            
        if enable == "yes":
            self.comm('AST ,0')
        if enable == "no":
            self.comm('AST ,1')

        #Default values, not currently choosable from function parameters
        self.comm('DSE ,0')  #Use default SEM voltage
        self.comm('DTY ,1')  #Use SEM for ion detection
        self.comm('AMO ,2')  #Auto-range
        self.comm('MMO ,3')  #Single mass measurement (opposed to mass-scan)
        self.comm('MRE ,15') #Peak resolution

    def create_mysql_measurement(self, channel, timestamp, masslabel, comment,
                                 metachannel=False, type=5):
        """ Creates a MySQL row for a channel.
        
        Create a row in the measurements table and populates it with the
        information from the arguments as well as what can be
        auto-generated.
        
        """
        #cnxn = MySQLdb.connect(host="servcinf", user="microreactor", 
        #                       passwd="microreactor", db="cinfdata")
        cnxn = MySQLdb.connect(host="servcinf", user=self.chamber, 
                               passwd=self.chamber, db="cinfdata")

        cursor = cnxn.cursor()
        
        if not metachannel:
            self.comm('SPC ,' + str(channel)) #Select the relevant channel       
            sem_voltage = self.comm('SHV')
            preamp_range = self.comm('AMO')
            if preamp_range == '2':
                preamp_range = '0' #Idicates auto-range in mysql-table
            else:
                preamp_range = "" #TODO: Here we should read the actual range
        else:
            sem_voltage = "-1"
            preamp_range = "-1"
        
        #TODO: We need a look-up table, this number is not physical
        timestep = self.comm('MSD') 
        
        query = ""
        query += 'insert into measurements_' + self.chamber + ' set mass_label="' 
        query += masslabel + '"'
        query += ', sem_voltage="' + sem_voltage + '", preamp_range="'
        query += preamp_range + '", time="' + timestamp + '", type="' + str(type) + '"'
        query += ', comment="' + comment + '"'

        cursor.execute(query)
        cnxn.commit()
        
        query = 'select id from measurements_' + self.chamber + ' order by id desc limit 1'
        cursor.execute(query)
        id_number = cursor.fetchone()
        id_number = id_number[0]
        cnxn.close()
        return(id_number)
    
    def create_ms_channellist(self, channel_list, timestamp, no_save=False):
        """ This function creates the channel-list and the associated mysql-entries """
        #TODO: Implement various ways of creating the channel-list

        ids = {}
        comment = channel_list[0]['comment']
        for i in range(1,len(channel_list)):
            ch = channel_list[i]
            self.config_channel(channel=i, mass=ch['mass'], speed=ch['speed'], enable="yes")
            self.channel_list[i] = {'masslabel':ch['masslabel'],'value':'-'}
            
            if no_save == False:
                ids[i] = self.create_mysql_measurement(i,timestamp,ch['masslabel'],comment)
            else:
                ids[i] = i
        ids[0] = timestamp
        logging.error(ids)
        return ids
        
    def mass_time(self,ms_channel_list, timestamp):
        self.operating_mode = "Mass Time"
        self.stop = False
        
        ns = len(ms_channel_list) - 1
        self.comm('CYM ,1') #0, single. 1, multi
        self.comm('CTR ,0') #Trigger mode, 0=auto trigger
        self.comm('CYS ,1') #Number of repetitions
        self.comm('CBE ,1') #First measurement channel in multi mode
        self.comm('CEN ,' + str(ns)) #Last measurement channel in multi mod

        start_time = time.time()
        ids = self.create_ms_channellist(ms_channel_list, timestamp, no_save=False)
        self.current_timestamp = ids[0]
    
        while self.stop == False:
            self.comm('CRU ,2') #Start measurement
            time.sleep(0.1)
            status = self.comm('MBH')
            status = status.split(',')
            channel = 0
            try:
                running = int(status[0])
            except:
                running = 1
                logging.warn('Could not read status, continuing measurement')
            while running == 0: 
                status = self.comm('MBH',debug=False)
                status = status.split(',')
                try:
                    running = int(status[0])
                except:
                    running = 1
                    logging.warn('Could not read status, continuing measurement')
                if len(status)>3:
                    for j in range(0,int(status[3])):
                        self.measurement_runtime = time.time()-start_time
                        value = self.comm('MDB')
                        channel = channel + 1
                        self.channel_list[channel]['value'] = value
                        sqltime = str((time.time() - start_time) * 1000)
                        query  = 'insert into '
                        query += 'xy_values_' + self.chamber + ' '
                        query += 'set measurement="' + str(ids[channel])
                        query += '", x="' + sqltime + '", y="' + value + '"'
                        if ord(value[0]) == 134:
                            running = 1
                            logging.warn('Bad value: ' + query)
                            break
                        else:
                            self.sqlqueue.put(query)
                        channel = channel % (len(ids)-1)
                        time.sleep(0.05)
                    time.sleep(0.1)
                else:
                    logging.error("Status error, continuing measurement")
        self.operating_mode = "Idling"
        
    def mass_scan(self):
        first_mass = 0
        scan_width = 50
        self.comm('CYM, 0') #0, single. 1, multi
        self.comm('SMC, 0') #Channel 0
        self.comm('MMO, 0')  #Mass scan, to enable FIR filter, set value to 1
        self.comm('MST ,2') #Steps
        self.comm('MSD ,10') #Speed
        self.comm('AMO, 2')  #Auto range electromter
        self.comm('MFM, ' + str(first_mass)) #First mass
        self.comm('MWI, ' + str(scan_width)) #Scan width
        #print "Mass-scan:   " + self.comm('MMO, 5')  #Magic mass-scan
        print "Resolution:  " + self.comm('MRE ,20')   #Resolution

        comment = 'Test mass scan'
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        id = self.create_mysql_measurement(i,timestamp,'Mass Scan',comment, type=4)

        start = time.time()
        self.comm('CRU ,2') #Start measurement
        status = self.comm('MBH')
        status = status.split(',')
        running = status[0]
        datax = []
        datay = []
        current_sample = 0
        while  int(running) == 0:
            #print "A"
            status = self.comm('MBH',debug=False)
            #print "B"
            print "Status: " + status
            status = status.split(',')
            running = status[0]
            time.sleep(1)
        #print len(datay)
        print "---"
        header = self.comm('MBH')
        print header
        header = header.split(',')
        print header[3]
        output_string = ""

        #fig = plt.figure()
        #axis = fig.add_subplot(1,1,1)

        start = time.time()
        number_of_samples = int(header[3])
        samples_pr_unit = 1.0 / (scan_width/float(number_of_samples))
        print "Number of samples: " + str(number_of_samples)
        print "Samples pr. unit: " + str(samples_pr_unit)
        for i in range(0,number_of_samples):
            val = self.comm('MDB')
            datay.append(float(val))
            datax.append(first_mass + i / samples_pr_unit)
            
            output_string += val + '\n'
        print time.time() - start
        #print output_string
        #axis.plot(datax,datay, 'r-')
        #plt.show()
        
        datfile = open('ms.dat','w')
        datfile.write(output_string)
        datfile.close()
        print time.time() - start
        
if __name__ == "__main__":
    sql_queue = Queue.Queue()
    sql_saver = SQL_saver.sql_saver(sql_queue,'microreactorNG')
    sql_saver.daemon = True
    sql_saver.start()

    qmg = QMG422(sql_queue)
    qmg.communication_mode(computer_control=True)
      
    printer = qmg_status_output.qmg_status_output(qmg,sql_saver_instance=sql_saver)
    printer.daemon = True
    printer.start()
 
    time.sleep(1)
    
    channel_list = {}
    channel_list[0] = {'comment':'DELETE'}
    channel_list[1] = {'mass':2,'speed':9, 'masslabel':'M2'}
    channel_list[2] = {'mass':4,'speed':9, 'masslabel':'M15'}
    channel_list[3] = {'mass':15,'speed':10, 'masslabel':'M18'}
    channel_list[4] = {'mass':28,'speed':9, 'masslabel':'M28'}
    channel_list[5] = {'mass':32,'speed':9, 'masslabel':'M32'}
    channel_list[6] = {'mass':44,'speed':10, 'masslabel':'M44'}

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    meta_udp = qmg_meta_channels.udp_meta_channel(qmg, timestamp, channel_list[0]['comment'], 5)
    meta_udp.create_channel('Temp, TC', 'rasppi12', 9999, 'tempNG')
    meta_udp.create_channel('Pirani buffer volume', 'rasppi07', 9997, 'read_buffer')
    meta_udp.create_channel('Pirani containment', 'rasppi07', 9997, 'read_containment')
    meta_udp.create_channel('RTD Temperature', 'rasppi05', 9992, 'read_rtdval')
    meta_udp.daemon = True
    meta_udp.start()

    meta_flow = qmg_meta_channels.compound_udp_meta_channel(qmg, timestamp, channel_list[0]['comment'],5,'rasppi16',9998, 'read_all')
    meta_flow.create_channel('Sample Pressure',0)
    meta_flow.create_channel('Flow, H2',4)
    meta_flow.create_channel('Flow, CO',6)
    meta_flow.daemon = True
    meta_flow.start()
    
    print qmg.mass_time(channel_list, timestamp)
    #qmg.scan_test()
    printer.stop()
    #print qmg.read_voltages()
    #print qmg.qms_status()
    print qmg.sem_status(voltage=1600, turn_on=True)
    print qmg.emission_status(current=0.1,turn_on=True)
    #print qmg.detector_status()
    #qmg.read_voltages()
    #print qmg.simulation()
    #print qmg.scan_test()
    #print qmg.single_mass()
    print qmg.qms_status()
