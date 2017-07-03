# pylint: disable=C0413
""" App for logging specific sockets into dateplots """
from __future__ import print_function
import threading
import sys
import socket
import time
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)
try:
    sys.path.append('/home/pi/PyExpLabSys/machines/' + sys.argv[1])
except IndexError:
    print('You need to give the name of the raspberry pi as an argument')
    print('This will ensure that the correct settings file will be used')
    exit()
import settings # pylint: disable=F0401

LOGGER = get_logger('Socket Dataplot Logger', level='ERROR', file_log=True,
                    file_name='errors.log', terminal_log=False, email_on_warnings=False)

class SocketReaderClass(threading.Thread):
    """ Read the wanted socket """
    def __init__(self, host, port, command):
        threading.Thread.__init__(self)
        self.host = host
        self.port = port
        self.command = command + '#raw'
        self.command = self.command.encode()
        self.current_value = None
        self.quit = False
        self.ttl = 10

    def value(self):
        """ return current value """
        self.ttl = self.ttl - 1
        print(self.ttl)
        if self.ttl > 0:
            return self.current_value
        else:
            self.quit = True
            # Consider to keep program running even in case of
            # socket failures


    def run(self):
        while not self.quit:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            try:
                sock.sendto(self.command, (self.host, self.port))
                received = sock.recv(1024)
                received = received.decode('ascii')
                self.current_value = float(received[received.find(',') + 1:])
                self.ttl = 20
            except (socket.timeout, ValueError) as e:
                print(e) # LOG THIS
            time.sleep(1)

def main():
    """ Main function """

    codenames = []
    for channel in settings.channels.values():
        channel['reader'] = SocketReaderClass(channel['host'], channel['port'],
                                              channel['command'])
        channel['reader'].start()
        channel['logger'] = ValueLogger(channel['reader'], comp_val=channel['comp_value'])
        channel['logger'].daemon = True
        channel['logger'].start()
        codenames.append(channel['codename'])

    try:
        port = settings.port_number
    except AttributeError:
        port = 9000
    pullsocket = DateDataPullSocket(settings.user + '-socket_logger',
                                    codenames, timeouts=5, port=port)
    pullsocket.start()

        
    db_logger = ContinuousDataSaver(continuous_data_table=settings.dateplot_table,
                                    username=settings.user,
                                    password=settings.passwd,
                                    measurement_codenames=codenames)
    db_logger.start()

    time.sleep(2)

    everything_ok = True
    while everything_ok:
        time.sleep(0.25)
        for channel in settings.channels.values():
            if not channel['reader'].isAlive():
                everything_ok = False
                # Report error here!!!
                # Consider to keep program running even in case of
                # socket failures
            value = channel['logger'].read_value()
            pullsocket.set_point_now(channel['codename'], value)
            if channel['logger'].read_trigged():
                print(value)
                db_logger.save_point_now(channel['codename'], value)
                channel['logger'].clear_trigged()

if __name__ == '__main__':
    main()
