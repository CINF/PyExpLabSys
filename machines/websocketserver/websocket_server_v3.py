# pylint: disable=C0103,R0904
"""This file implements the central websockets server for servcinf"""

from __future__ import print_function, division

import time
import threading
import json
#from SocketServer import BaseRequestHandler, ThreadingUDPServer
# Python 2/3 compatibility
try:
    import SocketServer
    from Queue import Queue
except ImportError:
    import socketserver as SocketServer
    from queue import Queue
from collections import Counter, defaultdict

# Used for logging output from twisted, see commented out lines below
#from twisted.python import log
from twisted.internet import reactor, ssl
from autobahn.twisted.websocket import (
    WebSocketServerFactory, WebSocketServerProtocol, listenWS
)

from PyExpLabSys.common import utilities
utilities.WARNING_EMAIL = 'jejsor@fysik.dtu.dk'
utilities.ERROR_EMAIL = 'jejsor@fysik.dtu.dk'
LOG = utilities.get_logger('ws-server2', level='info', file_log=True, file_max_bytes=10485760)

# Used only to count open connections
WEBSOCKET_IDS = set()

# Dictionary to keep track of subscriptions, keys are host:codename values is a set of
# websocket connections
SUBSCRIPTIONS = defaultdict(set)

# Used to keep track of last values, these will be sent upon subscription. Keys are hostname:codename
LAST = {}

# Data queue: (time_received, data_items, data_len)
DATA_QUEUE = Queue()

# Counter for performance metrics, keys are: json_decode_error, sent_n, sent_bytes,
# received_n, received_bytes
COUNTER = Counter()

# Delivery time
HANDLE_TIMES = [0]


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
            now = time.time()
            max_internal_handle_time = max(HANDLE_TIMES)
            del HANDLE_TIMES[:]
            HANDLE_TIMES.append(0)
            performance_stats = {
                'max_internal_handle_time': (now, max_internal_handle_time),
                'websocket_count': (now, len(WEBSOCKET_IDS)),
            }

            # TODO add thread count

            for key in ['received_n', 'sent_n', 'json_decode_error']:
                try:
                    amount = COUNTER.pop(key)
                except KeyError:
                    amount = 0
                performance_stats[key] = (now, amount)
            
            for key in ['received_', 'sent_']:
                try:
                    amount = COUNTER.pop(key + 'bytes')
                except KeyError:
                    amount = 0
                performance_stats[key + 'kb'] = (now, amount // 1024)

            data = {'host': 'cinf-wsserver', 'data': performance_stats}
            LOG.debug(performance_stats)
            DATA_QUEUE.put(
                (time.time(), data, len(json.dumps(data)))
            )

    def stop(self):
        """Stop the Load Monitor"""
        self._stop = True
        while self.isAlive():
            time.sleep(0.01)


### Receive Data Part
class ReceiveDataUDPHandler(SocketServer.BaseRequestHandler):
    """UDP Handler for receiving data"""

    def handle(self):
        raw = self.request[0].strip()
        data_length = len(raw)
        try:
            data = json.loads(raw)
        except ValueError:
            error = 'ERROR: Could not decode \'{}\' as json'.format(raw)
            LOG.error(error)
            COUNTER['json_decode_error'] += 1

        COUNTER['received_n'] += 1
        COUNTER['received_bytes'] += data_length
        DATA_QUEUE.put((time.time(), data, data_length))


class ReceiveDataUDPServer(threading.Thread):
    """Thread the runs the main UDP Server"""

    def __init__(self):
        super(ReceiveDataUDPServer, self).__init__()
        self.daemon = True
        # Setup threading UDP server
        host, port = "", 9767
        self.server = SocketServer.ThreadingUDPServer((host, port), ReceiveDataUDPHandler)

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
    """Thread that sends the data to subscribed websocket connections"""

    def __init__(self):
        super(DataSender, self).__init__()
        self.daemon = True

    def run(self):
        """Run main method in exception"""
        try:
            self.runner()
        except:
            LOG.exception('In data sender')
            raise

    def runner(self):
        """Main run method

        Pops data of the DATA_QUEUE and send it to the client that have subscribed to it
        """
        while True:
            time_received, data, data_length = DATA_QUEUE.get()

            # Soft stop
            if data == 'STOP':
                break

            # Get subscribed websockets and send the data packet to them
            receivers = self._get_receivers_and_set_last(data)

            for receiver in receivers:
                receiver.send_data(data)

            # Log the handle time for statistics purposes
            HANDLE_TIMES.append(time.time() - time_received)
            COUNTER['sent_n'] += len(receivers)
            COUNTER['sent_bytes'] += len(receivers) * data_length

    @staticmethod
    def _get_receivers_and_set_last(data):
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
        DATA_QUEUE.put((None, 'STOP', None))
        while self.isAlive():
            time.sleep(0.01)


class CinfWebSocketHandler(WebSocketServerProtocol):  # pylint: disable=W0232
    """Class that handles a websocket connection"""

    def _log(self, string, *args):
        """Logger with IP address prefix"""
        msg_string = 'ws {}: {}; {}'.format(self.peer, string, args)
        LOG.info(msg_string)
        print(string)
        print(self.peer)
        print(*args)

    def onOpen(self):
        """Log when the connection is opened"""
        WEBSOCKET_IDS.add(self)
        self._log('Connection opened count: %s', len(WEBSOCKET_IDS))

    def connectionLost(self, reason):
        """Log when the connection is lost"""
        self._log('Connection lost')
        WebSocketServerProtocol.connectionLost(self, reason)

    def onClose(self, wasClean, code, reason):
        """Log when the connection is closed"""
        try:
            WEBSOCKET_IDS.remove(self)
            self._log('Connection closed, count: %s', len(WEBSOCKET_IDS))
        except KeyError:
            self._log('Could not close connection, not open, count: %s', len(WEBSOCKET_IDS))

    def XX_onMessage(self, msg, binary):
        print(msg, binary)
        data = json.loads(msg.decode('utf8'))
        LOG.info(data)
        LOG.info(type(data))
            
    def onMessage(self, msg, binary):
        """Parse the command and send response"""
        data = json.loads(msg)
        action = data.get('action')
        if action == 'subscribe':
            # Send last data before making the subscription
            self._log('Got subscriptions: %s', data)
            last_messages = defaultdict(dict)
            for subscription in data['subscriptions']:
                try:
                    host, codename = subscription.split(':')
                except ValueError:
                    message =\
                        'ERROR: Incorrect subscription format {} from \'{}\'. '\
                        'Maybe you are trying to connect to version 1 of the '\
                        'Live Socket Proxy server, whereas I\'m version 2.'
                    message = message.format(data, self.peer.host)
                    LOG.warning(message)
                    self.send_data(message)
                    return
                if subscription in LAST:
                    last_messages[host][codename] = LAST[subscription]

            # Send last data in batches and as regular data
            for host, data_points in last_messages.items():
                self.send_data({'host': host, 'data': data_points})

            # Make subscription
            for subscription in data['subscriptions']:
                SUBSCRIPTIONS[subscription].add(self)
        else:
            LOG.error('wshandler: Unknown action: %s', action)

    def send_data(self, data):
        """json encode the message before sending it"""
        msg = json.dumps(data)
        self.sendMessage(msg.encode('utf8'))


def main():
    """ Main method for the websocket server """
    # Uncomment these two to get log from twisted (DEPRECATED)
    #import sys
    #log.startLogging(sys.stdout)
    # Create context factor with key and certificate

    # Start UDP server thread
    udp_server = ReceiveDataUDPServer()
    udp_server.start()

    # Start load monitor thread
    load_monitor = LoadMonitor()
    load_monitor.start()

    # Start the data sender thread
    data_sender = DataSender()
    data_sender.start()

    ####### SSL IMPLEMENTATION
    context_factory = ssl.DefaultOpenSSLContextFactory(
        '/home/service/certs/cinf-wsserver.key',
        '/home/service/certs/cinf-wsserver_fysik_dtu_dk.crt'
    )
    # Old certificate paths
    #'/home/kenni/certs/fysik.dtu.dk.key',
    #'/home/kenni/certs/fysik.dtu.dk-NEW.crt'
    # Form the webserver factory
    factory = WebSocketServerFactory("wss://localhost:9002")#, debug=True)
    # Set the handler
    factory.protocol = CinfWebSocketHandler
    # Listen for incoming WebSocket connections: wss://localhost:9002
    listenWS(factory, context_factory)
    ######## SSL IMPLEMENTATION END

    try:
        LOG.info('run reactor')
        reactor.run()  # pylint: disable=E1101
    except Exception as exception_:
        LOG.exception(exception_)
        raise exception_

    # Stop all three threads
    udp_server.stop()
    load_monitor.stop()
    data_sender.stop()

    LOG.info('main: Ended')
    #raw_input('All stopped. Press enter to exit')
    print('All stopped. Press enter to exit')

if __name__ == '__main__':
    main()
