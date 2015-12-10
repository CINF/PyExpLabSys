# pylint: disable=C0103,R0904
"""This file implements the central websockets server for servcinf"""

from __future__ import print_function

import time
import threading
import socket
import json
from Queue import Queue

# Used for logging output from twisted, see commented out lines below
#from twisted.python import log
from twisted.internet import reactor, ssl
from autobahn.websocket import WebSocketServerFactory, WebSocketServerProtocol, listenWS

from PyExpLabSys.common.utilities import get_logger
LOG = get_logger('ws-server', level='debug', file_log=True, file_max_bytes=10485760)

WEBSOCKET_IDS = set()  # Used only to count open connections

# Dictionary to keep track of subscriptions, keys are host:codename values is a set of
# websocket connections
SUBSCRIPTIONS = {}

# Data queue
DATA_QUEUE = Queue()


class DataSender(threading.Thread):
    """Send data to websocket connections"""

    def __init__(self):
        super(DataSender, self).__init__()
        self.daemon = True

    def run(self):
        start = time.time()
        while True:
            passed = time.time() - start
            start = time.time()
            for con in WEBSOCKET_CONNECTIONS:
                con.sendMessage(str(passed))
            time.sleep(0.1)
    


class CinfWebSocketHandler(WebSocketServerProtocol):  # pylint: disable=W0232
    """Class that handles a websocket connection"""

    def onOpen(self):
        """Log when the connection is opened"""
        WEBSOCKET_IDS.add(id(self))
        LOG.info('wshandler: Connection opened, count: %s', len(WEBSOCKET_IDS))
        self.sendMessage('yeah')

    def connectionLost(self, reason):
        """Log when the connection is lost"""
        LOG.info('wshandler: Connection lost')
        WebSocketServerProtocol.connectionLost(self, reason)

    def onClose(self, wasClean, code, reason):
        """Log when the connection is closed"""
        try:
            WEBSOCKET_IDS.remove(id(self))
            LOG.info('wshandler: Connection closed, count: %s', len(WEBSOCKET_IDS))
        except KeyError:
            LOG.info('wshandler: Could not close connection, not open, count: %s', len(WEBSOCKET_IDS))

    def onMessage(self, msg, binary):
        """Parse the command and send response"""
        print(msg)

    def json_send_message(self, data):
        """json encode the message before sending it"""
        self.sendMessage(json.dumps(data))




def main():
    """ Main method for the websocket server """
    # Uncomment these two to get log from twisted
    #import sys
    #log.startLogging(sys.stdout)
    # Create context factor with key and certificate




    ####### SSL IMPLEMENTATION
    # context_factory = ssl.DefaultOpenSSLContextFactory(
    #     '/home/kenni/certs/fysik.dtu.dk.key',
    #     '/home/kenni/certs/fysik.dtu.dk.crt'
    # )
    # # Form the webserver factory
    # factory = WebSocketServerFactory("wss://localhost:9001", debug=True)
    # # Set the handler
    # factory.protocol = CinfWebSocketHandler
    # # Listen for incoming WebSocket connections: wss://localhost:9001
    # listenWS(factory, context_factory)
    ######## SSL IMPLEMENTATION END

    #context_factory = ssl.DefaultOpenSSLContextFactory(
    #    '/home/kenni/certs/fysik.dtu.dk.key',
    #    '/home/kenni/certs/fysik.dtu.dk.crt'
    #)
    # Form the webserver factory
    factory = WebSocketServerFactory("ws://localhost:9001", debug=True)
    # Set the handler
    factory.protocol = CinfWebSocketHandler
    # Listen for incoming WebSocket connections: wss://localhost:9001
    listenWS(factory)#, context_factory)

    #ds = DataSender()
    #ds.start()

    try:
        reactor.run()  # pylint: disable=E1101
    except Exception as exception_:
        LOG.exception(exception_)
        raise exception_

    LOG.info('main: Ended')
    #raw_input('All stopped. Press enter to exit')
    print('All stopped. Press enter to exit')

if __name__ == '__main__':
    main()
