from __future__ import print_function
import serial
import time
import logging

LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
LOGGER.addHandler(logging.NullHandler())

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

    def ranges(self, index, reverse = False):
        """ Return the physical range of a returned index """
        range_values = [0] * 8
        range_values[0] = -5
        range_values[1] = -6
        range_values[2] = -7
        range_values[3] = -8
        if self.switch_9_and_11:
            range_values[4] = -11
            range_values[5] = -12
            range_values[6] = -9
            range_values[7] = -10
        else:
            range_values[4] = -9
            range_values[5] = -10
            range_values[6] = -11
            range_values[7] = -12
        if reverse:
            return range_values.index(int(index))
        else:
            return range_values[int(index)]

    def __init__(self, switch_range = False):
        self.f = serial.Serial('/dev/ttyUSB0', 9600)
        self.switch_9_and_11 = switch_range
        self.type = '420'
        self.communication_mode(computer_control=True)

    def comm(self, command):
        """ Communicates with Baltzers/Pferiffer Mass Spectrometer

        Implements the low-level protocol for RS-232 communication with the
        instrument. High-level protocol can be implemented using this as a
        helper

        """
        LOGGER.debug("Command in progress: " + command)

        waiting = self.f.inWaiting()
        if waiting > 0: #Skip characters that are currently waiting in line
            debug_info = self.f.read(waiting)
            LOGGER.debug("Elements not read: " + str(waiting) + 
                          ": Contains: " + debug_info)            

        commands_without_reply = ['SEM', 'EMI', 'SEV', 'OPM', 'CHA',
                                  'CHM', 'SPE', 'FIR', 'WID','RUN',
                                  'STP', 'RAN', 'CHA', 'SYN', 'CYC',
                                  'STA', 'DET', 'CTR']
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

    def simulation(self):
        """ Produces a simulated spectrum, does not work on qmg420 """
        pass

    def sem_status(self, voltage=-1, turn_off=False, turn_on=False):
        """ Get or set the SEM status """
        if voltage > -1:
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
        """ Set the integration speed """
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
        return emission_current, filament_on


    def detector_status(self, SEM=False, faraday_cup=False):
       return 'Not possible on this model'


    def read_voltages(self):
        """ Read the voltages on the lens system """
        print('Not possible on this QMG model')

    def set_channel(self, channel):
        """ Set the active measurement channel """
        self.comm('CHA ' + str(channel))


    def read_sem_voltage(self):
        """ Read the selected SEM voltage """
        sem_voltage = self.status('RDE', 4)
        return sem_voltage

    def read_preamp_range(self):
        """ Read the preamp range """
        preamp_index = self.status('RDE', 1)
        preamp_range = self.ranges(index=preamp_index)
        return preamp_range

    def read_timestep(self):
        timestep = self.status('RSC', 5)
        return timestep

    def measurement_running(self):
        """ Return true if measurement is running """
        running = self.comm('STW')[6] == '0'
        return running

    def mass_time(self, ns):
        """ Configure instrument for mass time """
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
            length = length - 2
        else:
            length = 0
        return length

    def communication_mode(self, computer_control=False):
        """ Set the qmg420 up for rs232 controll """
        self.comm('CTR 1')
        return True

    def first_mass(self, mass):
        """ Set the first mass of a mass scan or the current mass """
        self.comm('FIR ' + str(mass))

    def get_multiple_samples(self, number):
        """ Retrive more than one sample from the device """
        values = [0] * number
        for i in range(0, number):
            val = self.comm(chr(5))
            if not val == '':
                values[i] = val
        return values

    def get_single_sample(self):
        """ Retrieve a single sample from the device """
        error = 0
        while (self.waiting_samples() == 0) and (error < 40):
            time.sleep(0.2)
            error = error + 1
        if error > 39:
            LOGGER.error('Sample did arrive on time')
            value = ""
        else:
            value = self.comm(chr(5))
        return value

    def config_channel(self, channel, mass=-1, speed=-1, amp_range=-1, enable=""):
        """ Config a MS channel for measurement """
        self.set_channel(channel)
        self.comm('OPM 1')
        LOGGER.error('Wanted range, channel ' + str(channel) + ': ' + str(amp_range))

        if mass > -1:
            self.first_mass(mass)

        if speed > -1:
            self.speed(speed)

        if amp_range < -2:
            range_index = self.ranges(amp_range, reverse=True)
            LOGGER.error('Range, channel ' + str(channel) + str(range_index))
            self.comm('RAN ' + str(range_index))

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

    def mass_scan(self, first_mass, scan_width, amp_range=-7):
        self.comm('CHA 0')
        self.comm('OPM 0')
        self.comm('FIR ' + str(first_mass))
        self.comm('WID ' + str(scan_width))
        self.comm('SPE ' + str(10))
        range_index = self.ranges(amp_range, reverse=True)
        self.comm('RAN ' + str(range_index))
        self.comm('CHM 0') # Mass scan, to enable FIR filter, set value to 1
        self.comm('STA 1')
        self.comm('DET 1') # Use SEM for ion detection

