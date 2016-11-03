""" Module to check that local machine is living up to its duties """
import time
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.sockets import DateDataPullSocket
import threading
import socket
import sys
sys.path.append('/home/pi/PyExpLabSys/machines/' + sys.argv[1])
import settings # pylint: disable=F0401
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)
LOGGER = get_logger('Socket Supervisor')

class SocketSupervisor(threading.Thread):
    """ Supervisor will check that a list of ports are still open """
    def __init__(self):
        threading.Thread.__init__(self)
        self.quit = False
        self.ports = settings.ports
        self.setup = settings.setup
        self.pullsocket = DateDataPullSocket(self.setup + '-socket supervisor',
                                             [str(port) for port in self.ports],
                                             timeouts=len(self.ports)*[5])
        self.pullsocket.start()

    def run(self):
        """ Main loop """
        while not self.quit:
            for port in self.ports:
                time.sleep(1)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', port))
                if result == 0:
                    self.pullsocket.set_point_now(str(port), True)
                    print(port, True)
                else:
                    self.pullsocket.set_point_now(str(port), False)
                    print(port, False)

if __name__ == '__main__':
    SP = SocketSupervisor()
    SP.start()
