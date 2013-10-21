import serial

class qmg_422():

   def __init__(self):
       self.f = serial.Serial('/dev/ttyUSB0',19200)
       self.type = '422'

   def comm(self, command):
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


    def simulation(self):
        """ Chekcs wheter the instruments returns real or simulated data """
        ret_string = self.comm('TSI ,0')
        if int(ret_string) == 0:
            sim_state = "Simulation not running"
        else:
            sim_state = "Simulation running"
        return sim_state

    def set_channel(self, channel):
        self.comm('SPC ,' + str(channel)) #Select the relevant channel       

    def read_sem_voltage(self):
        sem_voltage = self.comm('SHV')
        return sem_voltage

    def read_preamp_range(self):
        preamp_range = self.comm('AMO')
        if preamp_range == '2':
           preamp_range = '0' #Idicates auto-range in mysql-table
        else:
           preamp_range = "" #TODO: Here we should read the actual range
        retun preamp_range

    def read_timestep(self):
        timestep = self.comm('MSD') 
        return timestep



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
        print "V01: " + self.comm('VO1') #0..150,   1V steps
        print "V02: " + self.comm('VO2') #0..125,   0.5V steps
        print "V03: " + self.comm('VO3') #-30..30,  0.25V steps
        print "V04: " + self.comm('VO4') #0..60,    0.25V steps
        print "V05: " + self.comm('VO5') #0..450,   2V steps
        print "V06: " + self.comm('VO6') #0..450,   2V steps
        print "V07: " + self.comm('VO7') #0..250,   1V steps
        print "V08: " + self.comm('VO8') #-125..125,1V steps 
        print "V09: " + self.comm('VO9') #0..60    ,0.25V steps


    def mass_scan(self, first_mass, scan_width):
        self.qmg.comm('CYM, 0') #0, single. 1, multi
        self.qmg.comm('SMC, 0') #Channel 0
        self.qmg.comm('MMO, 0')  #Mass scan, to enable FIR filter, set value to 1
        self.qmg.comm('MST ,2') #Steps
        self.qmg.comm('MSD ,10') #Speed
        self.qmg.comm('AMO, 2')  #Auto range electromter
        self.qmg.comm('MFM, ' + str(first_mass)) #First mass
        self.qmg.comm('MWI, ' + str(scan_width)) #Scan width
        #print "Mass-scan:   " + self.comm('MMO, 5')  #Magic mass-scan
        #print "Resolution:  " + self.comm('MRE ,20')   #Resolution

        data = {}
        data['x'] = []
        data['y'] = []

        self.qmg.comm('CRU ,2') #Start measurement
        status = self.qmg.comm('MBH')
        status = status.split(',')
        running = status[0]
        current_sample = 0
        while  int(running) == 0:
            #print "A"
            status = self.qmg.comm('MBH',debug=False)
            #print "B"
            print "Status: " + status
            status = status.split(',')
            running = status[0]
            time.sleep(1)
        #print len(datay)
        print "---"
        header = self.qmg.comm('MBH')
        print header
        header = header.split(',')
        print header[3]
        output_string = ""

        start = time.time()
        number_of_samples = int(header[3])
        samples_pr_unit = 1.0 / (scan_width/float(number_of_samples))
        print "Number of samples: " + str(number_of_samples)
        print "Samples pr. unit: " + str(samples_pr_unit)
        for i in range(0,number_of_samples):
            val = self.qmg.comm('MDB')
            data['y'].append(float(val))
            data['x'].append(first_mass + i / samples_pr_unit)
                        output_string += val + '\n'
        print time.time() - start
