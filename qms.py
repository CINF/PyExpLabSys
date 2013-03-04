import threading
import Queue
import serial
import time
import matplotlib.pyplot as plt
import MySQLdb
import curses

#class sql_saver(threading.Thread()):
#    def 


class QMG422():

    def __init__(self):
        self.f = serial.Serial('/dev/ttyUSB0',19200)
        self.sqlqueue = Queue.Queue()

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


    #Returns the communication mode
    def communication_mode(self,computer_control=False):
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
    
    """ This function creates the channel-list and the associated mysql-entries """
    def create_channellist(self,dummy=False):
        #TODO: Implement various ways of creating the channel-list instead of hard-coding it
        id = {}
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.config_channel(channel=1, mass=18, speed=11, enable="yes")
        self.config_channel(channel=2, mass=28, speed=11, enable="yes")
        self.config_channel(channel=3, mass=32, speed=11, enable="yes")
        self.config_channel(channel=4, mass=7,  speed=11, enable="yes")
        
        if dummy == False:
            id[1] = self.create_mysql_measurement(1,timestamp,"M18","First python mass-spec")
            id[2] = self.create_mysql_measurement(2,timestamp,"M28","First python mass-spec")
            id[3] = self.create_mysql_measurement(3,timestamp,"M32","First python mass-spec")
            id[4] = self.create_mysql_measurement(4,timestamp,"M7","First python mass-spec")
        else:
            id[1] = 1
            id[2] = 2
            id[3] = 3
            id[4] = 4

        return id
        

    def show_channel(self,channel):
        self.comm('CYM ,1') #0, single. 1, multi
        self.comm('CBE ,1') #First measurement channel in multi mode
        self.comm('CEN ,4') #Last measurement channel in multi mod
        self.comm('CTR ,0') #Trigger mode, 0=auto trigger
        self.comm('CYS ,1') #Number of repetitions
        start_time = time.time()
          
        id = self.create_channellist(dummy=True)
        
        #cnxn = MySQLdb.connect(host="servcinf",user="microreactor",passwd="microreactor",db="cinfdata")
        #cursor = cnxn.cursor()

        for iteration in range(0,100000000):
            print self.sqlqueue.qsize()
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
                        value = self.comm('MDB')
                        channel = channel + 1
                        sqltime = str((time.time() - start_time) * 1000)
                        query = 'insert into xy_values_dummy set measurement="' + str(id[channel]) + '", x="' + sqltime + '", y="' + value + '"'
                        if ord(value[0]) == 134:
                            running = 1
                            print query
                            break
                        else:
                            self.sqlqueue.put(query)
                            #cursor.execute(query)
                            #cnxn.commit()
                        channel = channel % 4
                        time.sleep(0.05)
                    time.sleep(0.1)
                else:
                    print "Status error, continuing measurement"
        cnxn.close()
        
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
    qmg = QMG422()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    #print qmg.create_mysql_measurement(1, timestamp, "M18","Test measurement")
    #print qmg.communication_mode()
    #print qmg.qms_status()
    #print qmg.sem_status(turn_on=True)
    #print qmg.emission_status(current=0.8,turn_on=True)
    #print qmg.detector_status()
    #qmg.read_voltages()
    #print qmg.simulation()
    #print qmg.scan_test()
    #print qmg.single_mass()
    print qmg.show_channel(1)
