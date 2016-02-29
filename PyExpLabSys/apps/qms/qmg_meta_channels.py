""" Module to perform read-out of meta channels for qms """

import threading
import time
import socket
import logging

LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
LOGGER.addHandler(logging.NullHandler())

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
        self.update_interval = update_interval
        self.time = timestamp
        self.comment = channel_list['ms'][0]['comment']
        self.qms = qms
        self.channel_list = []
        for i in range(1, len(channel_list['meta']) + 1):
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

        sql_id = self.qms.create_mysql_measurement(0, self.time, masslabel=masslabel,
                                                   amp_range=-1, comment=self.comment,
                                                   metachannel=True)
        channel = {}
        channel['id']   = sql_id
        channel['host'] = host
        channel['port'] = port
        channel['cmd']  = udp_string
        self.channel_list.append(channel)

    def run(self):
        start_time = time.time()
        while True:
            t_channel_start = time.time()
            for channel in self.channel_list:
                port = channel['port']
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(0.2)
                LOGGER.debug('Meta command: ' + channel['cmd'])
                try:
                    sock.sendto(channel['cmd'], (channel['host'], port))
                    received = sock.recv(1024)
                    received = received.strip()
                except socket.timeout:
                    received = ""
                LOGGER.debug('Meta recieve: ' + received)
                if channel['cmd'][-4:] == '#raw':
                    received = received[received.find(',')+1:]
                sock.close()
                try:
                    value = float(received)
                    LOGGER.error(str(value))
                    sqltime = str((time.time() - start_time) * 1000)
                except ValueError:
                    LOGGER.warn('Meta-channel, could not convert to float: ' + received)
                    value = None
                except TypeError:
                    LOGGER.warn('Type error from meta channel, most likely during shutdown')
                    value = None
                except Exception as e:
                    LOGGER.error('Unknown error: ' + str(e))
                    value = None

                if not value == None:
                    query  = 'insert into xy_values_' + self.qms.chamber + ' '
                    query += 'set measurement="'
                    query += str(channel['id']) + '", x="' + sqltime
                    query += '", y="' + str(value) + '"'
                    self.qms.sqlqueue.put((query, None))

            time_spend = time.time() - t_channel_start
            if time_spend < self.update_interval:
                time.sleep(self.update_interval - time_spend)
