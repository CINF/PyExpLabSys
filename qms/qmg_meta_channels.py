import threading
import time
import socket

class udp_meta_channel(threading.Thread):
    """ A class to handle meta data for the QMS program.

    Each instance of this class will communicate with several hosts via udp.
    Only a single update_interval can be used for all hosts in the channel list.
    """

    def __init__(self, qms, timestamp, channel_list, update_interval):
        """ Initalize the instance of the class
        
        Timestamps and comments are currently identical for all channels, since
        this is anyway the typical way the channels are used.
        """

        threading.Thread.__init__(self)
        self.ui = update_interval
        self.time = timestamp
        self.comment = channel_list['ms'][0]['comment']
        self.qms = qms
        self.channel_list = []
        for i in range(1,len(channel_list['meta'])+1):
            label = channel_list['meta'][i]['label']
            host = channel_list['meta'][i]['host']
            port = channel_list['meta'][i]['port']
            command = channel_list['meta'][i]['command']
            self.create_channel(label, host, port, command)

    def create_channel(self, masslabel, host, port, udp_string):
        """ Create a meta channel.

        Uses the SQL-communication function of the qms class to create a
        SQL-entry for the meta-channel.
        """

        id = self.qms.create_mysql_measurement(0, self.time, masslabel, self.comment, metachannel=True)
        channel = {}
        channel['id']   = id
        channel['host'] = host
        channel['port'] = port
        channel['cmd']  = udp_string
        self.channel_list.append(channel)

    def run(self):
        start_time= time.time()
        while True:
            t0 = time.time()
            for channel in self.channel_list:
                PORT = channel['port']
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(channel['cmd'] + "\n", (channel['host'], PORT))
                #try:
                received = sock.recv(1024)
                #sock.shutdown(socket.SHUT_RDWR)
                sock.close
                try:
                    value = float(received)
                    sqltime = str((time.time() - start_time) * 1000)
                except ValueError:
                    logging.warn('Meta-channel, could not convert to float: ' + received)
                    value = None
                except TypeError:
                    logging.warn('Type error from meta channel, most likely during shutdown')

                if not value == None:
                    query  = 'insert into xy_values_' + self.qms.chamber + ' '
                    query += 'set measurement="'
                    query += str(channel['id']) + '", x="' + sqltime
                    query += '", y="' + str(value) + '"'
                    self.qms.sqlqueue.put(query)

            time_spend = time.time() - t0
            if time_spend < self.ui:
                time.sleep(self.ui - time_spend)


class compound_udp_meta_channel(threading.Thread):
    """ A class to handle meta data for the QMS program.

    Each instance of this class will query a signle udp command, parse
    the output and log into as many seperate channels as wanted.
    """

    def __init__(self, qms, timestamp, comment, update_interval,hostname, port, udp_string):
        """ Initalize the instance of the class
        """

        threading.Thread.__init__(self)
        self.ui = update_interval
        self.time = timestamp
        self.comment = comment
        self.qms = qms
        self.channel_list = []
        self.hostname = hostname
        self.udp_string = udp_string
        self.port = port

    def create_channel(self, masslabel, position):
        """ Create a meta channel.

        Uses the SQL-communication function of the qmg class to create a
        SQL-entry for the meta-channel.
        """

        id = self.qms.create_mysql_measurement(0, self.time, masslabel, self.comment, metachannel=True)
        channel = {}
        channel['id']   = id
        channel['position'] = position
        self.channel_list.append(channel)

    def run(self):
        start_time= time.time()
        while True:
            t0 = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            #sock.setblocking(0)
            #try:
            sock.sendto(self.udp_string + "\n", (self.hostname, self.port))
            received = sock.recv(1024)
            #except:
            #    time.sleep(0.1)
            #    logging.warn('udp read time-out')
            #    break #Re-start the loop and query the udp server again

            sqltime = str((time.time() - start_time) * 1000)
            
            
            try:
                val_array = received.split(',')
                values = {}
                for channel in val_array:
                    val = channel.split(':')
                    values[int(val[0])] = float(val[1])
            except ValueError:
                logging.warn('Unable to parse udp compound string')
                break
                
            for channel in self.channel_list:
                try:
                    value = values[channel['position']]
                except:
                    value = None
                    logging.warn('Not enough values in compound udp string')
 
                if not value == None:
                    query  = 'insert into xy_values_' + self.qms.chamber + ' '
                    query += 'set measurement="'
                    query += str(channel['id']) + '", x="' + sqltime
                    query += '", y="' + str(value) + '"'
                    self.qms.sqlqueue.put(query)

            time_spend = time.time() - t0
            if time_spend < self.ui:
                time.sleep(self.ui - time_spend)
