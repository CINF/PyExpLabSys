# pylint: disable=E1101
""" Mass Spec Main program """
try:
    import Queue as queue
except ImportError:
    import queue
import time
import logging
import MySQLdb
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
LOGGER.addHandler(logging.NullHandler())

class QMS(object):
    """ Complete mass spectrometer """
    def __init__(self, qmg, sqlqueue=None, chamber='dummy', credentials='dummy',
                 livesocket=None):
        self.qmg = qmg
        if not sqlqueue is None:
            self.sqlqueue = sqlqueue
        else: #We make a dummy queue to make the program work
            self.sqlqueue = queue.Queue()
        self.operating_mode = "Idling"
        self.current_action = 'Idling'
        self.message = ''
        self.autorange = False
        self.livesocket = livesocket
        self.current_timestamp = "None"
        self.measurement_runtime = 0
        self.stop = False
        self.chamber = chamber
        self.credentials = credentials
        self.channel_list = {}
        LOGGER.info("Program started. Log level: " + str(LOGGER.getEffectiveLevel()))

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
        """ Report detector status """
        return self.qmg.detector_status(sem, faraday_cup)

    def read_voltages(self):
        """ Read the voltage of the lens system """
        self.qmg.read_voltages()

    def simulation(self):
        """ Chekcs wheter the instruments returns real or simulated data """
        self.qmg.simulation()

    def config_channel(self, channel, params, enable=""):
        """ Setup a channel for measurement """
        self.qmg.config_channel(channel, mass=params['mass'], speed=params['speed'],
                                amp_range=params['amp_range'], enable=enable)

    def create_mysql_measurement(self, channel, timestamp, masslabel, amp_range,
                                 comment, mass=0, metachannel=False,
                                 measurement_type=5):
        """ Creates a MySQL row for a channel.
        Create a row in the measurements table and populates it with the
        information from the arguments as well as what can be
        auto-generated.
        """
        cnxn = MySQLdb.connect(host="servcinf-sql", user=self.credentials,
                               passwd=self.credentials, db="cinfdata")

        cursor = cnxn.cursor()

        if not metachannel:
            self.qmg.set_channel(channel)
            sem_voltage = self.qmg.read_sem_voltage()
            preamp_range = str(amp_range)
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
        query += str(measurement_type) + '"' + ', comment="' + comment + '"'
        query += ', timestep=' + str(timestep) + ', actual_mass=' + str(mass)
        LOGGER.info(query)
        cursor.execute(query)
        cnxn.commit()

        query = 'select id from measurements_' + self.chamber + ' '
        query += 'order by id desc limit 1'
        cursor.execute(query)
        id_number = cursor.fetchone()
        id_number = id_number[0]
        cnxn.close()
        return id_number

    def read_ms_channel_list(self, filename='channel_list.txt'):
        """ Read and parse channel list """
        channel_list = {}
        channel_list['ms'] = {}
        channel_list['meta'] = {}

        channel_file = open(filename, 'r')
        datafile = channel_file.read()
        lines = datafile.split('\n')

        data_lines = []
        for line in lines:
            if (len(line) > 0) and (not line[0] == '#'):
                data_lines.append(line)

        ms_count = 1
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
                for j in range(0, len(params)):
                    params[j] = params[j].strip()
                label = params[params.index('masslabel') + 1]
                speed = int(params[params.index('speed') + 1])
                mass = float(params[params.index('mass') + 1])
                amp_range = int(params[params.index('amp_range') + 1])
                channel_list['ms'][ms_count] = {'masslabel':label, 'speed':speed,
                                                'mass':mass, 'amp_range':amp_range}
                ms_count += 1

            if key == 'meta_channel':
                params = items[1].split(',')
                for j in range(0, len(params)):
                    params[j] = params[j].strip()
                host = params[params.index('host')+1]
                port = int(params[params.index('port')+1])
                label = params[params.index('label')+1]
                command = params[params.index('command')+1]
                channel_list['meta'][meta] = {'host':host, 'port':port,
                                              'label':label, 'command':command}
                meta += 1

        #TODO: The channel list format should be changed so that the general
        #      parameters are in a third dictionary key
        channel_list['ms'][0] = {'comment':comment, 'autorange':autorange}

        return channel_list


    def create_ms_channellist(self, channel_list, timestamp, no_save=False):
        """ This function creates the channel-list and the
        associated mysql-entries """
        #TODO: Implement various ways of creating the channel-list
        #TODO: Implement working autorange
        ids = {}

        params = {'mass':99, 'speed':1, 'amp_range':-5}
        for i in range(0, 16):
            self.config_channel(i, params, enable='no')

        comment = channel_list[0]['comment']
        self.autorange = channel_list[0]['autorange']
        LOGGER.info('Autorange: ' + str(self.autorange))
        #Check for qmg-version 422 will do hardware autorange!

        for i in range(1, len(channel_list)):
            channel = channel_list[i]
            self.config_channel(channel=i, params=channel, enable="yes")
            self.channel_list[i] = {'masslabel':channel['masslabel'], 'value':'-'}

            if no_save is False:
                ids[i] = self.create_mysql_measurement(i, timestamp, mass=channel['mass'],
                                                       masslabel=channel['masslabel'],
                                                       amp_range=channel['amp_range'],
                                                       comment=comment)
            else:
                ids[i] = i
        ids[0] = timestamp
        LOGGER.error(ids)
        return ids

    def mass_time(self, ms_channel_list, timestamp, no_save=False):
        """ Perfom a mass-time scan """
        self.operating_mode = "Mass Time"
        self.stop = False
        number_of_channels = len(ms_channel_list) - 1
        self.qmg.mass_time(number_of_channels)

        start_time = time.time()
        ids = self.create_ms_channellist(ms_channel_list, timestamp, no_save=no_save)
        self.current_timestamp = ids[0]

        while self.stop is False:
            self.qmg.set_channel(1)
            self.qmg.start_measurement()
            #time.sleep(0.01)
            for channel in range(1, number_of_channels + 1):
                self.measurement_runtime = time.time()-start_time
                value = self.qmg.get_single_sample()
                #self.channel_list[channel]['value'] = value
                sqltime = str((time.time() - start_time) * 1000)
                if value == "":
                    break
                else:
                    try:
                        value = float(value)
                    except ValueError:
                        value = -1
                        LOGGER.error('Value error, could not convert to float')
                    if self.qmg.type == '422' and self.qmg.reverse_range is True:
                        amp_range = ms_channel_list[channel]['amp_range']
                        if amp_range in (-9, -10):
                            value = value * 100.0
                        if amp_range in (-11, -12):
                            value = value / 100.0
                    if self.qmg.type == '420':
                        LOGGER.error('Value: ' + str(value))
                        LOGGER.error(ms_channel_list[channel]['amp_range'])
                        range_val = 10**ms_channel_list[channel]['amp_range']
                        value = value * range_val
                        LOGGER.error('Range-value: ' + str(value))
                    query = 'insert into '
                    query += 'xy_values_' + self.chamber + ' '
                    query += 'set measurement="' + str(ids[channel])
                    query += '", x="' + sqltime + '", y="' + str(value) + '"'
                self.channel_list[channel]['value'] = str(value)
                if self.livesocket is not None:
                    self.livesocket.set_point_now('qms-value', value)
                if no_save is False:
                    self.sqlqueue.put((query, None))
                #time.sleep(0.25)
            #time.sleep(0.05)
        self.operating_mode = "Idling"

    def mass_scan(self, first_mass=0, scan_width=50,
                  comment='Mass-scan', amp_range=-7):
        """ Perform a mass scan """
        start_time = time.time()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.operating_mode = 'Mass-scan'
        sql_id = self.create_mysql_measurement(0, timestamp, 'Mass Scan',
                                               comment=comment, amp_range=amp_range,
                                               measurement_type=4)
        self.message = 'ID number: ' + str(sql_id) + '. Scanning from '
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

        query = ''
        query += 'insert into xy_values_' + self.chamber
        query += ' set measurement = ' + str(sql_id) + ', x = '
        self.current_action = 'Downloading samples from device'
        j = 0
        for i in range(0, int(number_of_samples / 100)):
            self.measurement_runtime = time.time()-start_time
            samples = self.qmg.get_multiple_samples(100)
            for i in range(0, len(samples)):
                j += 1
                new_query = query + str(first_mass + j / samples_pr_unit)
                if self.qmg.type == '420':
                    new_query += ', y = ' + str(float(samples[i]) *
                                                (10**amp_range))
                if self.qmg.type == '422':
                    if amp_range == 0:
                        new_query += ', y = ' + samples[i]
                    else:
                        new_query += ', y = ' + str((int(samples[i])/10000.0) *
                                                    (10**amp_range))

                self.sqlqueue.put((new_query, None))
        samples = self.qmg.get_multiple_samples(number_of_samples%100)
        for i in range(0, len(samples)):
            j += 1
            new_query = query + str(first_mass + j / samples_pr_unit)
            if self.qmg.type == '420':
                new_query += ', y = ' + str(float(samples[i])*(10**amp_range))
            if self.qmg.type == '422':
                if amp_range == 0:
                    new_query += ', y = ' + samples[i]
                else:
                    new_query += ', y = ' + str((int(samples[i])/10000.0) *
                                                (10**amp_range))

            self.sqlqueue.put((new_query, None))
        self.current_action = 'Emptying Queue'
        while not self.sqlqueue.empty():
            self.measurement_runtime = time.time()-start_time
            time.sleep(0.1)
        time.sleep(0.5)
