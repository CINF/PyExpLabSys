# pylint: disable=C0103,R0904
"""This file implements the central websockets server for servcinf"""

from __future__ import print_function

import time
import threading
import json
import SocketServer
from Queue import Queue
from collections import Counter, defaultdict

# Used for logging output from twisted, see commented out lines below
#from twisted.python import log
from twisted.internet import reactor, ssl
from autobahn.websocket import WebSocketServerFactory, WebSocketServerProtocol, listenWS

from PyExpLabSys.common.utilities import get_logger
LOG = get_logger('ws-server', level='debug', file_log=True, file_max_bytes=10485760)

# Used only to count open connections
WEBSOCKET_IDS = set()

# Dictionary to keep track of subscriptions, keys are host:codename values is a set of
# websocket connections
SUBSCRIPTIONS = defaultdict(set)

# Used to keep track of last values, these will be sent upon subscription. Keys are hostname:codename
LAST = {}

# Data queue: (time_received, data_items)
DATA_QUEUE = Queue()

# Counter for performance metrics
COUNTER = Counter()


### Load measurement
class LoadMonitor(threading.Thread):
    """Class that monitors the load on the websocket server"""

    def __init__(self):
        super(LoadMonitor, self).__init__()
        self.daemon = True
        self._stop = False

    def run(self):
        """Something something every second"""
        while not self._stop:
            time.sleep(1)
            for key in ['received_n', 'received_bytes']:
                try:
                    amount = COUNTER.pop(key)
                except KeyError:
                    amount = 0
                #print(key, amount, 'per second')

    def stop(self):
        """Stop the Load Monitor"""
        self._stop = True
        while self.isAlive():
            time.sleep(0.01)


### Receive Data Part
class ThreadingUDPServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    """Threding UDP Server"""


class ReceiveDataUDPHandler(SocketServer.BaseRequestHandler):
    """UDP Handler for receiving data"""

    def handle(self):
        raw = self.request[0].strip()
        socket = self.request[1]
        print(socket)
        try:
            data = json.loads(raw)
        except ValueError:
            error = 'ERROR: Could not decode \'{}\' as json'.format(raw)
            COUNTER['json_decode_error'] += 1
            socket.sendto(error, self.client_address)

        COUNTER['received_n'] += 1
        COUNTER['received_bytes'] += len(raw)
        DATA_QUEUE.put((time.time(), data))

        socket.sendto('OK', self.client_address)


class ReceiveDataUDPServer(threading.Thread):
    """Thread the runs the main UDP Server"""

    def __init__(self):
        super(ReceiveDataUDPServer, self).__init__()
        self.daemon = True
        host, port = "", 9767
        self.server = ThreadingUDPServer((host, port), ReceiveDataUDPHandler)

    def run(self):
        """Run method"""
        self.server.serve_forever()

    def stop(self):
        """Stop the UDP server"""
        LOG.info('UDP server stop called')
        self.server.shutdown()
        while self.isAlive():
            time.sleep(0.01)
        LOG.info('UDP server stopped')


class DataSender(threading.Thread):
    """Send data to websocket connections"""

    def __init__(self):
        super(DataSender, self).__init__()
        self.daemon = True

    def run(self):
        """Main run method

        Pops data of the DATA_QUEUE and send it to the client that have subscribed to it
        """
        while True:
            time_received, data = DATA_QUEUE.get()
            # Soft stop
            if data == 'STOP':
                break

            receivers = self._get_receivers_and_set_last(data)

            #print('Sending data to', len(receivers), 'receivers')
            for receiver in receivers:
                receiver.send_data(data)
            print('Handle time', time.time() - time_received)

    def _get_receivers_and_set_last(self, data):
        """Form the set of connections that should get this data package and set the value
        in LAST
        """
        receivers = set()
        hostname = data['host']
        for codename, value in data['data'].items():
            # form the subscription key as "hostname:codename"
            subscription_key = hostname + ':' + codename
            # Add the receivers for that data source
            for receiver in SUBSCRIPTIONS.get(subscription_key, set()):
                receivers.add(receiver)
            # And set the last value
            LAST[subscription_key] = value
        return receivers

    def stop(self):
        """Stop the data sender"""
        DATA_QUEUE.put((None, 'STOP'))
        while self.isAlive():
            time.sleep(0.01)


class CinfWebSocketHandler(WebSocketServerProtocol):  # pylint: disable=W0232
    """Class that handles a websocket connection"""

    def onOpen(self):
        """Log when the connection is opened"""
        WEBSOCKET_IDS.add(self)
        print(WEBSOCKET_IDS)
        LOG.info('wshandler: Connection opened, count: %s', len(WEBSOCKET_IDS))

    def connectionLost(self, reason):
        """Log when the connection is lost"""
        LOG.info('wshandler: Connection lost')
        WebSocketServerProtocol.connectionLost(self, reason)

    def onClose(self, wasClean, code, reason):
        """Log when the connection is closed"""
        try:
            WEBSOCKET_IDS.remove(self)
            LOG.info('wshandler: Connection closed, count: %s', len(WEBSOCKET_IDS))
        except KeyError:
            LOG.info('wshandler: Could not close connection, not open, count: %s', len(WEBSOCKET_IDS))

    def onMessage(self, msg, binary):
        """Parse the command and send response"""
        data = json.loads(msg)
        action = data.get('action')
        if action == 'subscribe':
            for subscription in data['subscriptions']:
                SUBSCRIPTIONS[subscription].add(self)
        else:
            print('BAD')
        print(SUBSCRIPTIONS)

    def send_data(self, data):
        """json encode the message before sending it"""
        self.sendMessage(json.dumps(data))




def main():
    """ Main method for the websocket server """
    # Uncomment these two to get log from twisted
    #import sys
    #log.startLogging(sys.stdout)
    # Create context factor with key and certificate

    udp_server = ReceiveDataUDPServer()
    udp_server.start()

    load_monitor = LoadMonitor()
    load_monitor.start()

    data_sender = DataSender()
    data_sender.start()

    ####### SSL IMPLEMENTATION
    context_factory = ssl.DefaultOpenSSLContextFactory(
        '/home/kenni/certs/fysik.dtu.dk.key',
        '/home/kenni/certs/fysik.dtu.dk-NEW.crt'
    )
    # Form the webserver factory
    factory = WebSocketServerFactory("wss://localhost:9002", debug=True)
    # Set the handler
    factory.protocol = CinfWebSocketHandler
    # Listen for incoming WebSocket connections: wss://localhost:9002
    listenWS(factory, context_factory)
    ######## SSL IMPLEMENTATION END

    #ds = DataSender()
    #ds.start()

    try:
        print('reactor run')
        reactor.run()  # pylint: disable=E1101
    except Exception as exception_:
        LOG.exception(exception_)
        raise exception_

    udp_server.stop()
    load_monitor.stop()
    data_sender.stop()

    LOG.info('main: Ended')
    #raw_input('All stopped. Press enter to exit')
    print('All stopped. Press enter to exit')

if __name__ == '__main__':
    main()
