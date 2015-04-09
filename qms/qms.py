import Queue
import time
#import matplotlib.pyplot as plt
import MySQLdb
import logging
import sys
sys.path.append('../')
import SQL_saver

import qmg_status_output
#import qmg_meta_channels
#import read_ms_channel_list

import qmg420
#import  qmg422

class qms():

    def __init__(self, qmg, sqlqueue=None, loglevel=logging.ERROR):
        self.qmg = qmg
        if not sqlqueue == None:
            self.sqlqueue = sqlqueue
        else: #We make a dummy queue to make the program work
            self.sqlqueue = Queue.Queue()
        self.operating_mode = "Idling"
        self.current_action = 'Idling'
        self.message = ''
        self.autorange = False
        self.current_timestamp = "None"
        self.measurement_runtime = 0
        self.stop = False
        self.chamber = 'dummy'
        self.credentials = 'dummy'
        self.channel_list = {}
        
        #Clear log file
        with open('qms.txt', 'w'):
            pass
        logging.basicConfig(filename="qms.txt", level=logging.INFO,
                            format='%(asctime)s %(message)s')
        logging.info("Program started. Log level: " + str(loglevel))
        # logging.basicConfig(level=logging.INFO)
        logging.basicConfig(level=logging.DEBUG)
        

    def communication_mode(self, computer_control=False):
        """ Set communication for computer control """
        return self.qmg.communication_mode(computer_control)

    def emission_status(self, current=-1, turn_off=False, turn_on=False):
        """ Return emission status """
        return self.qmg.emission_status(current, turn_off, turn_on)

    def sem_status(self, voltage=-1, turn_off=False, turn_on=False):
        """ Return the status of SEM """
        return self.qmg.sem_status(voltage, turn_off, turn_on)

    def detector_status(self, sem=False, faraday_cup=False):
        return self.qmg.detector_status(sem, faraday_cup)

    def read_voltages(self):
        """ Read the voltage of the lens system """
        self.qmg.read_voltages()

    def simulation(self):
        """ Chekcs wheter the instruments returns real or simulated data """
        self.qmg.simulation()

    def config_channel(self, channel, mass=-1, speed=-1, amp_range=0, enable=""):
        self.qmg.config_channel(channel, mass=mass, speed=speed,
                                amp_range=amp_range, enable=enable)


    def create_mysql_measurement(self, channel, timestamp, masslabel, comment,
                                 metachannel=False, type=5):
        """ Creates a MySQL row for a channel.
        
        Create a row in the measurements table and populates it with the
        information from the arguments as well as what can be
        auto-generated.
        
        """
        cnxn = MySQLdb.connect(host="servcinf", user=self.sql_credentials, 
                               passwd=self.sql_credentials, db="cinfdata")

        cursor = cnxn.cursor()
        
        if not metachannel:
            self.qmg.set_channel(channel)
            sem_voltage = self.qmg.read_sem_voltage()
            preamp_range = str(self.qmg.read_preamp_range())
            timestep = self.qmg.read_timestep()
            #TODO: We need a look-up table, this number is not physical
        else:
            sem_voltage = "-1"
            preamp_range = "-1"
            timestep = "-1"
                
        query = ""
        query += 'insert into measurements_' + self.chamber 
        query += ' set mass_label="'  + masslabel + '"'
        query += ', sem_voltage="' + sem_voltage + '", preamp_range="'
        query += preamp_range + '", time="' + timestamp + '", type="'
        query += str(type) + '"' + ', comment="' + comment + '"'

        cursor.execute(query)
        cnxn.commit()
        
        query = 'select id from measurements_' + self.chamber + ' '
        query += 'order by id desc limit 1'
        cursor.execute(query)
        id_number = cursor.fetchone()
        id_number = id_number[0]
        cnxn.close()
        return(id_number)


    def read_ms_channel_list(self, filename='channel_list.txt'):
        channel_list = {}
        channel_list['ms'] = {}
        channel_list['meta'] = {}

        f = open(filename, 'r')
        datafile = f.read()
        lines = datafile.split('\n')

        data_lines = []
        for line in lines:
            if (len(line) > 0) and (not line[0] == '#'):
                data_lines.append(line)

        ms = 1
        meta = 1
        for line in data_lines:
            items = line.split(':')
            key = items[0].lower().strip()
            if key == 'comment':
                comment = items[1].strip()

            if key == 'autorange':
                autorange = items[1].lower().strip() == 'yes'

            if key == 'ms_channel':
                params = items[1].split(',')
                for j in range(0,len(params)):
                    params[j] = params[j].strip()
                label = params[params.index('masslabel') + 1]
                speed = int(params[params.index('speed') + 1])
                mass = params[params.index('mass') + 1]
                amp_range = int(params[params.index('amp_range') + 1])
                channel_list['ms'][ms] = {'masslabel':label, 'speed':speed,'mass':mass,'amp_range':amp_range}
                ms += 1

            if key == 'meta_channel':
                params = items[1].split(',')
                for j in range(0, len(params)):
                    params[j] = params[j].strip()
                host = params[params.index('host')+1]
                port = int(params[params.index('port')+1])
                label = params[params.index('label')+1]
                command = params[params.index('command')+1]
                channel_list['meta'][meta] = {'host':host, 'port':port,'label':label,'command':command}
                meta += 1

        #TODO: The channel list format should be changed so that the general
        #      parameters are in a third dictionary key
        channel_list['ms'][0] = {'comment':comment, 'autorange':autorange}

        return channel_list


    def create_ms_channellist(self, channel_list, timestamp, no_save=False):
        """ This function creates the channel-list and the
        associated mysql-entries """
        #TODO: Implement various ways of creating the channel-list
        #TODO: Implement version 2.0 of autorange with deeper autorange
        ids = {}
        
        for i in range(0, 16):
            self.config_channel(i, mass=99, speed=1, amp_range=-1, enable='no')

        comment = channel_list[0]['comment']
        self.autorange = channel_list[0]['autorange']
        logging.info('Autorange: ' + str(self.autorange))
        #Check for qmg-version 422 will do hardware autorange!

        for i in range(1, len(channel_list)):
            ch = channel_list[i]
            self.config_channel(channel=i, mass=ch['mass'],
                                speed=ch['speed'],
                                amp_range=ch['amp_range'],
                                enable="yes")
            self.channel_list[i] = {'masslabel':ch['masslabel'], 'value':'-'}

            if no_save == False:
                ids[i] = self.create_mysql_measurement(i, timestamp,
                                                       ch['masslabel'], comment)
            else:
                ids[i] = i
        ids[0] = timestamp
        logging.error(ids)
        return ids
        
    def mass_time(self, ms_channel_list, timestamp):
        """ Perfom a mass-time scan """
        self.operating_mode = "Mass Time"
        self.stop = False
        number_of_channels = len(ms_channel_list) - 1
        self.qmg.mass_time(number_of_channels)

        start_time = time.time()
        ids = self.create_ms_channellist(ms_channel_list,
                                         timestamp, no_save=False)
        self.current_timestamp = ids[0]
        
        while self.stop == False:
            if self.autorange:
                for i in range(1, number_of_channels + 1):
                    #TODO: Decrease measurement time during autorange
                    self.config_channel(channel=i, amp_range=-5)
                self.qmg.set_channel(1)
                self.qmg.start_measurement()
                time.sleep(0.1)
                ranges = {}
                autorange_complete = False
                while not autorange_complete:
                    for i in range(1, number_of_channels + 1):
                        value = self.qmg.get_single_sample()
                        #logging.info(value)
                        try:
                            value = float(value)
                        except:
                            logging.warn('Missing value during auto-range')
                            autorange_complete = False
                            break
                        if value > 0.9:
                            ranges[i] = 2
                        if (value<0.9) and (value>0.09):
                            ranges[i] = 4
                        if (value<0.09) and (value>0.009):
                            ranges[i] = 5
                        if (value<0.009) and (value>0.0009):
                            ranges[i] = 6
                        if value < 0.0009:
                            ranges[i] = 7
                        autorange_complete = True
                if autorange_complete:
                    for i in range(1, number_of_samples + 1):
                        self.config_channel(channel=i, amp_range=ranges[i])
                        ms_channel_list[i]['amp_range'] = ranges[i]

            self.qmg.set_channel(1)
            self.qmg.start_measurement()
            time.sleep(0.1)
            for channel in range(1, number_of_channels + 1):
                self.measurement_runtime = time.time()-start_time
                value = self.qmg.get_single_sample()
                self.channel_list[channel]['value'] = value
                sqltime = str((time.time() - start_time) * 1000)
                if value == "":
                    break
                else:
                    try:
                        value = float(value)
                    except ValueError:
                        value = -1
                        logging.error('Value error, could not convert to float')
                    if self.qmg.type == '420':
                        logging.error('Value: ' + str(value))
                        logging.error(ms_channel_list[channel]['amp_range'])
                        range_val = 10**ms_channel_list[channel]['amp_range']
                        value = value * range_val
                        logging.error('Range-value: ' + str(value))
                    query  = 'insert into '
                    query += 'xy_values_' + self.chamber + ' '
                    query += 'set measurement="' + str(ids[channel])
                    query += '", x="' + sqltime + '", y="' + str(value) + '"'
                self.sqlqueue.put(query)
                time.sleep(0.25)
            time.sleep(0.1)
        self.operating_mode = "Idling"

    def mass_scan(self, first_mass=0, scan_width=50,
                  comment='Mass-scan', amp_range=-7):
        """ Perform a mass scan """
        start_time = time.time()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.operating_mode = 'Mass-scan'
        id = self.create_mysql_measurement(0, timestamp, 'Mass Scan',
                                           comment, type=4)
        self.message = 'ID number: ' + str(id) + '. Scanning from '
        self.message += str(first_mass) + ' to '
        self.message += str(first_mass+scan_width) + 'amu'
        self.current_timestamp = timestamp
        self.qmg.mass_scan(first_mass, scan_width, amp_range)

        self.measurement_runtime = time.time()-start_time

        self.qmg.start_measurement()
        self.current_action = 'Performing scan'
        time.sleep(0.1) #Allow slow qmg models time to start measurement
        while self.qmg.measurement_running():
            self.measurement_runtime = time.time()-start_time
            time.sleep(1)

        number_of_samples = self.qmg.waiting_samples()
        samples_pr_unit = 1.0 / (scan_width/float(number_of_samples))

        query  = '' 
        query += 'insert into xy_values_' + self.chamber 
        query += ' set measurement = ' + str(id) + ', x = '
        self.current_action = 'Downloading samples from device'
        j = 0
        for i in range(0, number_of_samples / 100):
            self.measurement_runtime = time.time()-start_time
            samples = self.qmg.get_multiple_samples(100)
            for i in range(0, len(samples)):
                j += 1
                new_query = query + str(first_mass + j / samples_pr_unit)
                if self.qmg.type == '420':
                    new_query += ', y = ' + str(float(samples[i]) *
                                                (10**amp_range))
                else:
                    new_query += ', y = ' + str(samples[i])
                self.sqlqueue.put(new_query)
        samples = self.qmg.get_multiple_samples(number_of_samples%100)
        for i in range(0, len(samples)):
            j += 1
            new_query = query + str(first_mass + j / samples_pr_unit)
            if self.qmg.type == '420':
                new_query += ', y = ' + str(float(samples[i])*(10**amp_range))
            else:
                new_query += ', y = ' + str(samples[i])

            self.sqlqueue.put(new_query)

        self.current_action = 'Emptying Queue'
        while not self.sqlqueue.empty():
            self.measurement_runtime = time.time()-start_time
            time.sleep(0.1)
        time.sleep(0.5)
