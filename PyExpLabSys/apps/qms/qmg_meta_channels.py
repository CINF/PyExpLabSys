""" Module to perform read-out of meta channels for qms """
import threading
import time
import socket
import logging
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
LOGGER.addHandler(logging.NullHandler())

class MetaChannels(threading.Thread):
    """ A class to handle meta data for the QMS program """

    def __init__(self, qms, timestamp, channel_list):
        """ Initalize the instance of the class """
        threading.Thread.__init__(self)
        self.timestamp = timestamp
        self.comment = channel_list['ms'][0]['comment']
        self.qms = qms
        self.channels = []
        channel_data = {}
        for i in range(1, len(channel_list['meta']) + 1):
            channel_data['repeat_interval'] = channel_list['meta'][i]['repeat_interval']
            channel_data['label'] = channel_list['meta'][i]['label']
            channel_data['host'] = channel_list['meta'][i]['host']
            channel_data['port'] = channel_list['meta'][i]['port']
            channel_data['cmd'] = channel_list['meta'][i]['command']
            self.create_channel(channel_data)

    def create_channel(self, channel_data):
        """ Create a meta channel.

        Uses the SQL-communication function of the qms class to create a
        SQL-entry for the meta-channel.
        """

        sql_id = self.qms.create_mysql_measurement(0, self.timestamp,
                                                   masslabel=channel_data['label'],
                                                   amp_range=-1, comment=self.comment,
                                                   metachannel=True)
        channel_data['id'] = sql_id
        channel_data['value'] = -1
        reader = UdpChannel(channel_data, self.qms, self.timestamp)
        reader.start()
        self.channels.append(reader)


class UdpChannel(threading.Thread):
    """ A class to handle meta data for the QMS program.
    Each instance of this class will communicate with a hosts via udp.
    """

    def __init__(self, channel_data, qms, timestamp):
        """ Initalize the instance of the class """
        threading.Thread.__init__(self)
        self.channel_data = channel_data.copy()
        self.timestamp = timestamp
        LOGGER.info(channel_data)
        self.qms = qms
        self.daemon = True

    def run(self):
        start_time = (time.mktime(self.timestamp.timetuple()) +
                      self.timestamp.microsecond / 1000000.0)
        while True:
            t_channel_start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.2)
            LOGGER.debug('Meta command: %s', self.channel_data['cmd'])

            try:
                sock.sendto(self.channel_data['cmd'].encode('ascii'),
                            (self.channel_data['host'], self.channel_data['port']))
                received = sock.recv(1024)
            except socket.timeout:
                received = b""
                LOGGER.warning('Socket timeout: %s', self.channel_data['cmd'])
            try:
                received = received.strip().decode()
            except UnicodeDecodeError:
                received = ""
                LOGGER.warning('Unicode Decode Error: %s', received)
            LOGGER.debug('Meta recieve: %s', received)
            if self.channel_data['cmd'][-4:] == '#raw':
                received = received[received.find(',')+1:]
            sock.close()

            try:
                value = float(received)
                LOGGER.debug(str(value))
                sqltime = str((time.time() - start_time) * 1000)
            except ValueError:
                LOGGER.warning('Meta-channel, could not convert to float: %s', received)
                value = None
            except TypeError:
                LOGGER.warning('Type error from meta channel, most likely during shutdown')
                value = None
            except Exception as e: # pylint: disable=broad-except
                LOGGER.error('Unknown error: %s', e)
                value = None
            self.channel_data['value'] = value

            if not value is None:
                query = 'insert into xy_values_' + self.qms.chamber + ' '
                query += 'set measurement="'
                query += str(self.channel_data['id']) + '", x="' + sqltime
                query += '", y="' + str(value) + '"'
                self.qms.sqlqueue.put((query, None))


            time_spend = time.time() - t_channel_start
            if time_spend < self.channel_data['repeat_interval']:
                time.sleep(self.channel_data['repeat_interval'] - time_spend)
