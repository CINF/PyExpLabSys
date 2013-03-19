import threading
import Queue
import serial
import time
#import matplotlib.pyplot as plt
import MySQLdb
import curses
import logging

class sql_saver(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue
        self.cnxn = MySQLdb.connect(host="servcinf",user="microreactor",passwd="microreactor",db="cinfdata")
        self.cursor = self.cnxn.cursor()
        self.commits = 0
        self.commit_time = 0
        
    def run(self):
        while True:
            self.queue
            start = time.time()
            query = self.queue.get()
            self.cursor.execute(query)
            self.cnxn.commit()
            self.commits += 1
            self.commit_time = time.time() - start
        self.cnxn.close()

class qmg422_status_output(threading.Thread):

    def __init__(self, qmg_instance,sql_saver_instance = None):
        threading.Thread.__init__(self)

        self.qmg = qmg_instance
        if not sql_saver_instance == None:
            self.sql = sql_saver_instance
        else:
            self.sql = None

        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)
        
    def run(self):
        while True:
            operating_mode = "Operating mode: " + self.qmg.operating_mode
            self.screen.addstr(1, 1, self.qmg.operating_mode)
            
            if self.qmg.operating_mode == "Mass Time":
                timestamp = "Timestamp: " + self.qmg.current_timestamp
                self.screen.addstr(3, 1, timestamp)
                runtime = "Experiment runtime: {0:.1f}s".format(qmg.measurement_runtime)
                self.screen.addstr(4, 1, runtime)
            
            if not self.sql == None:
                commits = "SQL commits: {0:.0f}".format(self.sql.commits)
                self.screen.addstr(3, 40, commits)
                commit_time = "Last commit duration: {0:.1f}".format(self.sql.commit_time) 
                self.screen.addstr(4, 40, commit_time)
            
            n = self.screen.getch()
            if n == ord('q'):
                qmg.stop = True
                
            self.screen.refresh()
            time.sleep(1)

    def stop(self):
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()    


class QMG422():

    def __init__(self,sqlqueue=None,curses_print=False):
        self.f = serial.Serial('/dev/ttyS1',19200)
        if not sqlqueue == None:
            self.sqlqueue = sqlqueue
        else: #We make a dummy queue to make the program work
            self.sqlqueue = Queue.Queue()
        self.operating_mode = "Idling"
        self.current_timestamp = "None"
        self.measurement_runtime = 0
        self.stop = False

    def comm(self,command,debug=False):
        t = time.time()
        if debug:
            print "Bebug! Begin!"
            print "Debug! Command in progress: " + command

        n = self.f.inWaiting()
        if n>0: #Skip characters that are currently waiting in line
            debug_info = self.f.read(n)
            if debug: #Remember this!!! After some MDB commands, this string is not empty!
                print "Elements not read: " + str(n) + ": Contains: " + debug_info
            
        ret = " "
        error_counter = 0
        while not ret[0] == chr(6):
            error_counter += 1
            self.f.write(command + '\r')
            ret = self.f.readline()

            if debug:
                print "Debug: Error counter: " + str(error_counter)
                print "Debug! In waiting: " + str(n)
                #print "Debug! Value of ret: "
                #for i in range(0,n):
                #    print ord(ret[i])
            if error_counter > 3:
                print "Communication error: " + str(error_counter)

        #We are now quite sure the instrument is ready to give back data        
        self.f.write(chr(5))
        ret = self.f.readline()

        if debug:
            print "Debug! Number in waiting after enq: " + str(n)
            print "Debug! Return value after enq:" + ret
            print "Debug! Ascii value of last char in ret: " + str(ord(ret[-1]))
        
        if (ret[-1] == chr(10)) or (ret[-1] == chr(13)):
            #print ord(ret[-1])
            ret_string = ret.strip()
        else:
            #ret_string = "Communication error"
            print "Hmmmm"
            self.f.write(chr(5))
            time.sleep(0.05)
            n = self.f.inWaiting()
            ret = self.f.read(n)
            print n
            print ret
            print "+++++++++++++++++"
        
        if debug:
            print "Debug! Debug end!!!!!!!\n\n\n\n\n"
        #print time.time() - t
        return ret_string

    def communication_mode(self,computer_control=False):
        #Returns the communication mode
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

    def emission_status(self,current=-1,turn_off=False,turn_on=False):
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

    def sem_status(self,voltage=-1,turn_off=False,turn_on=False):
        if voltage>-1:
            ret_string = self.comm('SHV ,' + str(voltage))
        else:
            ret_string = self.comm('SHV')
        print "SEM_STATUS: " + ret_string
        sem_voltage = int(ret_string)


        if turn_off ^ turn_on: #Only accept self-consistent sem-changes
            if turn_off:
                self.comm('SEM ,0')
            if turn_on:
                self.comm('SEM ,1')
        ret_string = self.comm('SEM')
        sem_on = ret_string == "1"
        
        return sem_voltage, sem_on

    def detector_status(self,SEM=False,faraday_cup=False):
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
        print "V01: " + self.comm('VO1') #0..150,   1V steps
        print "V02: " + self.comm('VO2') #0..125,   0.5V steps
        print "V03: " + self.comm('VO3') #-30..30,  0.25V steps
        print "V04: " + self.comm('VO4') #0..60,    0.25V steps
        print "V05: " + self.comm('VO5') #0..450,   2V steps
        print "V06: " + self.comm('VO6') #0..450,   2V steps
        print "V07: " + self.comm('VO7') #0..250,   1V steps
        print "V08: " + self.comm('VO8') #-125..125,1V steps 
        print "V09: " + self.comm('VO9') #0..60    ,0.25V steps

    def config_channel(self,channel,mass=-1,speed=-1,enable=""):
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

    def create_mysql_measurement(self,channel,timestamp,masslabel,comment):
        cnxn = MySQLdb.connect(host="servcinf",user="microreactor",passwd="microreactor",db="cinfdata")
        cursor = cnxn.cursor()
        
        self.comm('SPC ,' + str(channel))
        
        sem_voltage = self.comm('SHV')
        preamp_range = self.comm('AMO')
        if preamp_range == '2':
            preamp_range = '0' #Idicates auto-range in mysql-table
        else:
            preamp_range = "" #Here we should read the actual fixed range
        
        timestep = self.comm('MSD') #Here we need a look-up table, this number is not physical
        query = ""
        query += 'insert into measurements_dummy set mass_label="' + masslabel + '"'
        query += ', sem_voltage="' + sem_voltage + '", preamp_range="' + preamp_range + '", time="' + timestamp + '", type="5"'
        query += ', comment="' + comment + '"'
        cursor.execute(query)
        cnxn.commit()
        
        query = "select id from measurements_dummy order by id desc limit 1"
        cursor.execute(query)
        id_number = cursor.fetchone()
        id_number = id_number[0]
        cnxn.close()
        return(id_number)
    
    def create_ms_channellist(self,channel_list,no_save=False):
        """ This function creates the channel-list and the associated mysql-entries """
        #TODO: Implement various ways of creating the channel-list
        ids = {}
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        comment = channel_list[0]['comment']
        for i in range(1,len(channel_list)):
            ch = channel_list[i]
            self.config_channel(channel=i, mass=ch['mass'], speed=ch['speed'], enable="yes")
        
            if no_save == False:
                ids[i] = self.create_mysql_measurement(i,timestamp,ch['masslabel'],comment)
            else:
                ids[i] = i
        ids[0] = timestamp
        
        return ids
        

    def mass_time(self,ms_channel_list):
        self.operating_mode = "Mass Time"
        self.stop = False
        
        ns = len(ms_channel_list) - 1
        self.comm('CYM ,1') #0, single. 1, multi
        self.comm('CTR ,0') #Trigger mode, 0=auto trigger
        self.comm('CYS ,1') #Number of repetitions
        self.comm('CBE ,1') #First measurement channel in multi mode
        self.comm('CEN ,' + str(ns)) #Last measurement channel in multi mod

        start_time = time.time()
        ids = self.create_ms_channellist(ms_channel_list,no_save=False)
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
                #print "Error in converting status bit to int"
                #print status
            while running == 0: 
                status = self.comm('MBH',debug=False)
                status = status.split(',')
                try:
                    running = int(status[0])
                except:
                    running = 1
                    print "Error in converting status bit to int"
                if len(status)>3:
                    for j in range(0,int(status[3])):
                        self.measurement_runtime = time.time()-start_time
                        value = self.comm('MDB')
                        channel = channel + 1
                        sqltime = str((time.time() - start_time) * 1000)
                        query = 'insert into xy_values_dummy set measurement="' + str(ids[channel]) + '", x="' + sqltime + '", y="' + value + '"'
                        if ord(value[0]) == 134:
                            running = 1
                            print query
                            break
                        else:
                            self.sqlqueue.put(query)
                        channel = channel % 4
                        time.sleep(0.05)
                    time.sleep(0.1)
                else:
                    print "Status error, continuing measurement"
        self.operating_mode = "Idling"
        
    def scan_test(self):
        first_mass = 0
        scan_width = 150
        self.comm('MMO, 1')  #Mass scan, to enable FIR filter, set value to 1
        self.comm('MST ,1') #Steps
        self.comm('MSD ,10') #Speed
        self.comm('AMO, 2')  #Auto range electromter
        self.comm('MFM, ' + str(first_mass)) #First mass
        self.comm('MWI, ' + str(scan_width)) #Scan width
        #print "Mass-scan:   " + self.comm('MMO, 5')  #Magic mass-scan
        print "Resolution:  " + self.comm('MRE ,20')   #Resolution

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

        fig = plt.figure()
        axis = fig.add_subplot(1,1,1)

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
        axis.plot(datax,datay, 'r-')
        plt.show()
        """
        datfile = open('ms.dat','w')
        datfile.write(output_string)
        datfile.close()
        print time.time() - start
        """

    def single_mass(self):
        self.comm('CYM ,0') #0, single. 1, multi
        self.comm('SPC ,0')
        self.comm('SMC ,0')
        self.comm('MMO, 3')  #Single mass
        self.comm('MSD ,9') #Speed, 8:0.2s, 10:1.0s, 12:5s, 14:20s
        self.comm('AMO, 2')  #Auto range electromter
        self.comm('MFM, 18') #First mass

        fig = plt.figure()
        axis = fig.add_subplot(1,1,1)

        data18 = []
        data28 = []

        for i in range(0,3):
            self.comm('MFM, 18') #First mass
            self.comm('CRU ,2') #Start measurement
            status = self.comm('MBH',debug=False)
            status = status.split(',')
            running = status[0]
            while  int(running) == 0:
                status = self.comm('MBH',debug=False)
                #print "Status: " + status + " !"
                status = status.split(',')
                running = status[0]
                time.sleep(0.2)    
            value = float(self.comm('MDB'))
            data18.append(value)
            
            self.comm('MFM, 28') #First mass
            self.comm('CRU ,2') #Start measurement
            status = self.comm('MBH',debug=False)
            status = status.split(',')
            running = status[0]
            while  int(running) == 0:
                status = self.comm('MBH',debug=False)
                #print "Status: " + status + " !"
                status = status.split(',')
                running = status[0]
                time.sleep(0.2)    
            value = float(self.comm('MDB'))
            data28.append(value)
            

        axis.plot(data18,'b-')        
        axis.plot(data28,'r-')        
        plt.show(block=True)

    def simulation(self):
        ret_string = self.comm('TSI ,0')
        if int(ret_string) == 0:
            sim_state = "Simulation not running"
        else:
            sim_state = "Simulation running"
        return sim_state

    def qms_status(self):
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

if __name__ == "__main__":
    sql_queue = Queue.Queue()
    
    sql_saver = sql_saver(sql_queue)
    sql_saver.daemon = True
    sql_saver.start()

    qmg = QMG422(sql_queue)

    #printer = qmg422_status_output(qmg,sql_saver_instance=sql_saver)
    #printer.daemon = True
    #printer.start()
 
    time.sleep(1)
    channel_list = {}
    channel_list[0] = {'comment':'Slightly more fancy program now'}
    channel_list[1] = {'mass':18,'speed':11, 'masslabel':'M18'}
    channel_list[2] = {'mass':28,'speed':11, 'masslabel':'M28'}
    channel_list[3] = {'mass':32,'speed':11, 'masslabel':'M32'}
    channel_list[4] = {'mass':44,'speed':11, 'masslabel':'M44'}
    channel_list[4] = {'mass':7,'speed':11, 'masslabel':'M7'}

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    #print qmg.create_mysql_measurement(1, timestamp, "M18","Test measurement")
    #print qmg.communication_mode(computer_control=True)
    print qmg.qms_status()
    #print qmg.sem_status(turn_on=True)
    #print qmg.emission_status(current=0.8,turn_on=True)
    #print qmg.detector_status()
    #qmg.read_voltages()
    #print qmg.simulation()
    #print qmg.scan_test()
    #print qmg.single_mass()
    #print qmg.mass_time(channel_list)

    #printer.stop()
