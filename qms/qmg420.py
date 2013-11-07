import serial
import time
import logging

class qmg_420():

    def speeds(self, n):
        speeds = {}
        speeds[0]  = 0.0005
        speeds[1]  = 0.001
        speeds[2]  = 0.002
        speeds[3]  = 0.005
        speeds[4]  = 0.01
        speeds[5]  = 0.02
        speeds[6]  = 0.05
        speeds[7]  = 0.1
        speeds[8]  = 0.2
        speeds[9]  = 0.5
        speeds[10] = 1
        speeds[11] = 2
        speeds[12] = 5
        speeds[13] = 10
        speeds[14] = 20
        speeds[15] = 60
        return speeds[n]


    def __init__(self):
        self.f = serial.Serial('/dev/ttyUSB0',9600)
        self.type = '420'

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

        commands_without_reply = ['SEM', 'EMI', 'SEV', 'OPM', 'CHA', 'CHM', 'SPE', 'FIR', 'WID','RUN', 'STP', 'RAN', 'CHA', 'SYN', 'CYC', 'STA']
        self.f.write(command + '\r')
        mem = command.split(' ')[0]
        if not mem in commands_without_reply:
            ret_string = self.f.readline()
        else:
            ret_string = ""
        ret_string = ret_string.replace('\n','')
        ret_string = ret_string.replace('\r','')
        return ret_string


    def status(self, command, index):
        status = self.comm(command)
        data = status[:-2].split(',')
        ret_string = data[index]
        return ret_string


    def communication_mode(self, computer_control=False):
       pass

    def simulation(self):
       pass


    def sem_status(self, voltage=-1, turn_off=False, turn_on=False):
        """ Get or set the SEM status """
        if voltage>-1:
            self.comm('SEM ' + str(voltage))
            ret_string = self.status('RDE', 4)
        else: #NOT IMPLEMENTED
            ret_string = self.status('RDE', 4)

        sem_voltage = int(ret_string)

        if turn_off ^ turn_on: #Only accept self-consistent sem-changes
            if turn_off:
                self.comm('SEV 0')
            if turn_on:
                self.comm('SEV 1')

        ret_string = self.status('ROP', 2)
        sem_on = ret_string == "1"
        
        return sem_voltage, sem_on


    def speed(self, speed):
        if speed > 3:
            self.comm('SPE ' + str(speed))
        return self.speeds(speed)


    def emission_status(self, current=-1, turn_off=False, turn_on=False):
        """ Get or set the emission status. """

        emission_current = -1
 
        if turn_off ^ turn_on:
            if turn_off:
                self.comm('EMI 0')
            if turn_on:
                self.comm('EMI 1')
        ret_string = self.status('ROP', 3)

        filament_on = ret_string == '1'
        return emission_current,filament_on

    def detector_status(self, SEM=False, faraday_cup=False):
       return 'Not possible on this model'


    def read_voltages(self):
        print 'Not possible on this QMG model'


    def set_channel(self, channel):
        self.comm('CHA ' + str(channel)) #Select the relevant channel       


    def read_sem_voltage(self):
        sem_voltage = self.status('RDE', 4)
        return sem_voltage

    def read_preamp_range(self):
        preamp_range = self.status('RDE', 1)
        return preamp_range

    def read_timestep(self):
        timestep = self.status('RSC', 5)
        return timestep

    def measurement_running(self):
        running = self.comm('STW')[6] == '0'
        return running

    def mass_time(self, ns):
        self.comm('OPM 1') #0, single. 1, multi
        #self.comm('CTR ,0') #Trigger mode, 0=auto trigger
        self.comm('CYC 1') #Number of repetitions
        #self.comm('CBE ,1') #First measurement channel in multi mode
        #self.comm('CEN ,' + str(ns)) #Last measurement channel in multi mod

    def start_measurement(self):
        self.comm('RUN')

    def waiting_samples(self):
        length = int(self.comm('RBC'))
        if length > 2:
            samples = length - 2
        else:
            length = 0
        return length

    def communication_mode(self, computer_control=False):
        return ''

    def first_mass(self, mass):
        self.comm('FIR ' + str(mass))

    def config_channel(self, channel, mass=-1, speed=-1, amp_range=-1,enable=""):
        """ Config a MS channel for measurement """
        self.set_channel(channel)
        self.comm('OPM 1')
        
        if mass>-1:
            self.first_mass(mass)
            
        if speed>-1:
            self.speed(speed)

        if amp_range>-1:
            self.comm('RAN ' + str(amp_range))
            
        if enable == "yes":
            self.comm('STA 1')
        if enable == "no":
            self.comm('STA 0')
 
        #Default values, not currently choosable from function parameters
        #self.comm('DSE ,0')  #Use default SEM voltage
        #self.comm('DTY ,1')  #Use SEM for ion detection
        self.comm('CHM 2')  #Single mass measurement (opposed to mass-scan)
        #self.comm('CHM 3')  #peak processor
        #self.comm('MRE ,15') #Peak resolution



    def mass_scan(self, first_mass, scan_width):
        self.comm('FIR ' + str(first_mass))
        self.comm('WID ' + str(scan_width))
        self.comm('OPM 0')
        self.comm('CHA 0')
        self.comm('CHM 0') # Mass scan, to enable FIR filter, set value to 1
        self.comm('STA 1')

        self.speed(8)

        status = self.comm('RSC').split(',')
        steps = status[7]
        speed = status[5]
        print status
        print speed

        if steps == '0':
           measurements_pr_step = 64
        if steps == '1':
           measurements_pr_step = 32
        if steps == '2':
           measurements_pr_step = 16

        if speed < 3:
            measurements_pr_step = measurements_pr_step / 2    
            
        if speed < 1:
            measurements_pr_step = measurements_pr_step / 2    

        number_of_samples = measurements_pr_step * scan_width
        samples_pr_unit = 1.0 / (scan_width/float(number_of_samples))
        self.start_measurement()
        time.sleep(0.5)
        running = self.measurement_running()
        while running:
           running = self.measurement_running()
           print running
           time.sleep(1)

        t = time.time()
        header = self.comm('HEA').split(',')

        data = {}
        data['x'] = []
        data['y'] = []
        
        for i in range(0,number_of_samples):
           val = self.comm(chr(5))
           print i
           data['y'].append(float(val) + 1e-5)
           data['x'].append(first_mass + i / samples_pr_unit)

        return data
