import threading
import Queue
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


class qms():

    def __init__(self, qmg, sqlqueue=None, loglevel=logging.ERROR):
        self.qmg = qmg
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
        

    def communication_mode(self, computer_control=False):
        return self.qmg.communication_mode(computer_control)

    def emission_status(self, current=-1, turn_off=False, turn_on=False):
        return self.qmg.emission_status(current, turn_off, turn_on)

    def sem_status(self, voltage=-1, turn_off=False, turn_on=False):
        return self.qmg.sem_status(voltage, turn_off, turn_on)

    def detector_status(self, SEM=False, faraday_cup=False):
        return self.qmg.detector_status(SEM, faraday_cup)

    def read_voltages(self):
        self.qmg.read_voltages()

    def simulation(self):
        """ Chekcs wheter the instruments returns real or simulated data """
        self.qmg.simulation()

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
            self.qmg.set_channel(channel)
            sem_voltage = self.qmg.read_sem_voltage()
            preamp_range = self.qmg.read_preamp_range()
            timestep = self.qmg.read_timestep()   #TODO: We need a look-up table, this number is not physical
        else:
            sem_voltage = "-1"
            preamp_range = "-1"
            timestep = "-1"
                
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
        

    def mass_scan(self, first_mass=0, scan_width=50):

        data = self.qmg.mass_scan(first_mass, scan_width)

        comment = 'Test scan - qgm420'
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        id = self.create_mysql_measurement(0,timestamp,'Mass Scan',comment, type=4, metachannel=True)
        #NOT A META-CHANNEL. Update create_mysql_measurement
        print id
        print len(data['x'])
        for i in range(0, len(data['x'])):
            query = 'insert into xy_values_' + self.chamber + ' set measurement = ' + str(id) + ', x = ' + str(data['x'][i]) + ', y = ' + str(data['y'][i])
            self.sqlqueue.put(query)
        
if __name__ == "__main__":
    sql_queue = Queue.Queue()
    sql_saver = SQL_saver.sql_saver(sql_queue,'microreactorNG')
    sql_saver.daemon = True
    sql_saver.start()

    qms = qms(sql_queue)
    qms.communication_mode(computer_control=True)
      
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
