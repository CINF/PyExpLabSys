""" Module to check that local machine is living up to its duties """
import time
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.sockets import LiveSocket
import socket
import sys
sys.path.append('/home/pi/PyExpLabSys/machines/' + sys.argv[1])
import settings # pylint: disable=F0401

LOGGER = get_logger('Socket Supervisor')

class SocketSupervisor(object):
    """ Supervisor will check that a list of ports are still open """
    def __init__(self):
        self.ports = settings.ports
        self.setup = settings.setup
        self.livesocket = LiveSocket(self.setup + '-socket supervisor',
                                     [str(port) for port in self.ports], 2)
        self.livesocket.start()

    def main(self):
        """ Main loop """
        for port in self.ports:
            time.sleep(1)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:
                print "Port is open"
            else:
                print "Port is not open"
