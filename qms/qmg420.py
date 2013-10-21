import serial
import time
import logging

class qmg_420():

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

        commands_without_reply = ['SEM', 'EMI', 'SEV', 'OPM', 'CHA', 'CHM', 'SPE', 'FIR', 'WID','RUN', 'STP', 'RAN']
        self.f.write(command + '\r')
        mem = command.split(' ')[0]
        if not mem in commands_without_reply:
            ret_string = self.f.readline()
        else:
            ret_string = ""
        ret_string = ret_string.replace('\n','')
        ret_string = ret_string.replace('\r','')
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

    def status(self, command, index):
        status = self.comm(command)
        data = status[:-2].split(',')
        ret_string = data[index]
        return ret_string

    def mass_scan(self, first_mass, scan_width):
        self.comm('FIR ' + str(first_mass))
        self.comm('WID ' + str(scan_width))
        self.comm('OPM 0')
        self.comm('CHA 0')
        self.comm('CHM 0') # Mass scan, to enable FIR filter, set value to 1

        steps = self.comm('RSC').split(',')[7]
        if steps == '0':
           measurements_pr_step = 64
        if steps == '1':
           measurements_pr_step = 32
        if steps == '2':
           measurements_pr_step = 16
            
        number_of_samples = measurements_pr_step * scan_width
        samples_pr_unit = 1.0 / (scan_width/float(number_of_samples))
        print samples_pr_unit
        self.comm('RUN')
        time.sleep(0.5)
        print self.comm('HEA')
        print self.comm('STW')[8]
        running = self.comm('STW')[6] == '0'
        while running:
           print self.comm('HEA')
           running = self.comm('STW')[6] == '0'
           time.sleep(0.5)

        t = time.time()
        header = self.comm('HEA').split(',')

        data = {}
        data['x'] = []
        data['y'] = []
        
        for i in range(0,number_of_samples):
           val = self.comm(chr(5))
           data['y'].append(float(val))
           data['x'].append(first_mass + i / samples_pr_unit)

        return data
