# pylint: disable=C0103,R0904
"""This file implements the central websockets server for servcinf"""

import time
import threading
import socket
import json
import xml.etree.ElementTree as XML

# Used for logging output from twisted, see commented out lines below
#from twisted.python import log
from twisted.internet import reactor, ssl
from autobahn.websocket import WebSocketServerFactory, \
    WebSocketServerProtocol, listenWS

from PyExpLabSys.common.sockets import LiveSocket
LIVESOCKET = None
from PyExpLabSys.common.utilities import get_logger
LOG = get_logger('ws-server', level='debug', file_log=True,
                 file_max_bytes=10485760)

MALFORMED_SUBSCRIPTION = 'Error: Malformed subscription line: {}'
DATA = {}
TIME_REPORT_ALIVE = 60  # Seconds between the thread reporting in
WEBSOCKET_IDS = set()  # Used only to count open connections
CURRENT_CONNECTIONS = '/home/kenni/PyExpLabSys/machines/websocketserver/'\
                      'current_connections'


def current_log(text):
    """Log a message to the current file"""
    with open(CURRENT_CONNECTIONS, 'a') as file_:
        file_.write(text + '\n')


class CinfWebSocketHandler(WebSocketServerProtocol):  # pylint: disable=W0232
    """Class that handles a websocket connection"""

    def onOpen(self):
        """Log when the connection is opened"""
        WEBSOCKET_IDS.add(id(self))
        LOG.info('wshandler: Connection opened, count: {}'.
                 format(len(WEBSOCKET_IDS)))
        self.subscriptions = []  # pylint: disable=W0201

    def connectionLost(self, reason):
        """Log when the connection is lost"""
        LOG.info('wshandler: Connection lost')
        WebSocketServerProtocol.connectionLost(self, reason)

    def onClose(self, wasClean, code, reason):
        """Log when the connection is closed"""
        try:
            WEBSOCKET_IDS.remove(id(self))
            LOG.info('wshandler: Connection closed, count: {}'.
                     format(len(WEBSOCKET_IDS)))
        except KeyError:
            LOG.info('wshandler: Could not close connection, not open, '
                     'count: {}'.format(len(WEBSOCKET_IDS)))

    def onMessage(self, msg, binary):
        """Parse the command and send response"""
        if not binary:
            if msg.startswith('subscribe'):
                self.subscribe(msg)
            else:
                self.get_data(msg)

    def subscribe(self, msg):
        """Subscribe for a set of codenames for a specific hostname_port"""
        # msg is on the form: subscribe#hostname:port;codename1,codename2...
        LOG.info('wshandler: subscribe called with: ' + msg)
        _, args = msg.split('#')
        hostname_port, codenames_string = args.split(';')
        codenames = codenames_string.split(',')
        if hostname_port == '' or '' in codenames:
            msg = MALFORMED_SUBSCRIPTION.format(msg)
            LOG.warning('wshandler: ' + msg)
        else:
            number = len(self.subscriptions)
            self.subscriptions.append((hostname_port, codenames))
            msg += '#{}#{}'.format(number, DATA[hostname_port]['sane_interval'])
        self.json_send_message(msg)

    def get_data(self, msg):
        """Get data for a subscription number"""
        LOG.debug('wshandler: get_data called with: ' + msg)
        try:
            number = int(msg)
        except TypeError:
            out = 'Invalid subscription: ' + msg
        else:
            if number in range(len(self.subscriptions)):
                hostname_port, codenames = self.subscriptions[number]
                out = [number, []]
                for codename in codenames:
                    index_in_global = \
                        DATA[hostname_port]['codenames'].index(codename)
                    out[1].append(DATA[hostname_port]['data'][index_in_global])
            else:
                out = 'Invalid subscription number: ' + msg

        self.json_send_message(out)

    def json_send_message(self, data):
        """json encode the message before sending it"""
        self.sendMessage(json.dumps(data))


class UDPConnection(threading.Thread):
    """Class that handles an UDP connection to one data provider"""

    def __init__(self, hostname_port):
        LOG.info('{}: __init__ start'.format(hostname_port))
        super(UDPConnection, self).__init__()
        self.daemon = True
        self._stop = False
        self.hostname_port = hostname_port
        self.hostname, self.port = hostname_port.split(':')
        self.port = int(self.port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # If the sane interval cannot be retrived within 2 seconds, the
        # connection will stop itself
        self.socket.settimeout(2)
        sane_interval = self._send_and_get('sane_interval')
        codenames = self._send_and_get('codenames')
        if sane_interval is None or codenames is None:
            LOG.info('{}: Could not retrieve sane interval or codenames. '
                     'Make thread stop without performing any action'
                     .format(hostname_port)
            )
            self._stop = True
        else:
            DATA[hostname_port]['sane_interval'] = sane_interval
            LOG.info('{}: sane_interval {} retrieved'.format(
                hostname_port, sane_interval)
            )
            self.socket.settimeout(sane_interval * 2)

            DATA[hostname_port]['codenames'] = codenames
            LOG.info('{}: codenames {} retrieved'.format(
                hostname_port, str(codenames))
            )
        LOG.info('{}: __init__ ended'.format(hostname_port))

    def run(self):
        LOG.info('{}: run start'.format(self.hostname_port))
        while not self._stop:
            data = self._send_and_get('data')
            if data is None:
                LOG.info('{}: Get data timed out, stopping!'
                         .format(self.hostname_port))
                self._stop = True
                current_log(self.hostname_port + ' stopped')
            else:
                DATA[self.hostname_port]['data'] = data
                LOG.debug('{}: Retrieved data {}'.
                          format(self.hostname_port, data))

            time.sleep(DATA[self.hostname_port]['sane_interval'])

        LOG.info('{}: run ended'.format(self.hostname_port))
        current_log('{}: run ended'.format(self.hostname_port))

    def stop(self):
        """Stops the UPD connection"""
        LOG.info('{}: stop'.format(self.hostname_port))
        self._stop = True

    def _send_and_get(self, command):
        """ Send command and get response """
        self.socket.sendto(command, (self.hostname, self.port))
        try:
            data, _ = self.socket.recvfrom(1024)
            data = json.loads(data)
        except socket.timeout:
            self.stop()
            data = None
        return data


class UDPConnectionSteward(threading.Thread):
    """Class that creates and manages the UDP connections"""

    def __init__(self):
        LOG.info('steward: __init__ start')
        super(UDPConnectionSteward, self).__init__()
        self._stop = False
        self.daemon = True
        # Seconds between updating the web socket definitions from the
        # web_sockets.xml file
        self.update_interval = 90
        # Time interval between checking if it is time for an update
        self.main_interval = 1
        # The UDP definitions are a set of hostname:port strings
        self.udp_definitions = set()
        # The UDP definitions are used as keys for the UDP connections
        self.udp_connections = {}
        LOG.info('steward: __init__ end')

    def run(self):
        """Keeps the UPD connections up to date by deleting dead connections
        and synchronizing the connections with the web socket definitions in
        web_sockets.xml file
        """
        LOG.info('steward: run start')
        # Time of last update, force one on first run
        time0 = time.time() - self.update_interval
        while not self._stop:
            if time.time() - time0 > self.update_interval:
                LOG.info('steward: Checking the connections')
                # Delete dead UPD connections
                self._delete_dead_connections()

                # Update the UDP defs ..
                self._update_udp_definitions()
                # .. and get the defs from the existing connections ..
                udp_connection_keys = set(self.udp_connections.keys())
                # .. and calculate new and removed
                add = self.udp_definitions - udp_connection_keys
                delete = udp_connection_keys - self.udp_definitions

                if self.udp_definitions == udp_connection_keys:
                    LOG.info('steward: Connections up to date')

                # Delete removed connections
                self._delete_removed_connections(delete)
                # Add new connections
                self._add_new_connections(add)

                # Update time of last update
                time0 = time.time()

            # Update values on the live socket
            LIVESOCKET.set_point_now('wss_clients', float(len(WEBSOCKET_IDS)))
            LIVESOCKET.set_point_now('wss_hosts_defined',
                                     float(len(self.udp_definitions)))
            LIVESOCKET.set_point_now('wss_hosts',
                                     float(len(self.udp_connections)))
            time.sleep(self.main_interval)
        LOG.info('steward: run ended')

    def stop(self):
        """ Ask the thread to stop """
        LOG.info('steward: stop')
        self._stop = True
        while self.is_alive():
            time.sleep(self.main_interval)

        # Stop all the UPD connections
        sane = 0.1
        for hostname_port, connection in self.udp_connections.items():
            LOG.info('steward: Stopping thread {0}'.format(hostname_port))
            sane = max(sane, DATA[hostname_port]['sane_interval'])
            connection.stop()
        LOG.debug('steward: Largest sane interval: ' + str(sane))

        # Check that they have indeed stopped
        still_running = True
        while still_running:
            time.sleep(sane)
            still_running = False
            for connection in self.udp_connections.values():
                still_running = still_running or connection.is_alive()
            LOG.debug('steward: Connections still running: ' +
                      str(still_running))

        LOG.info('steward: stop ended')
        # Prevent python from tearing down the environment before all threads
        # have shut down nicely
        time.sleep(1)

    def _update_udp_definitions(self):
        """Scan the web_sockets.xml file for udp connection definitions and
        update the UDP definitions set in self.udp_definitions.

        The UDP definitions consist simply of hostname:port strings e.g:
        'rasppi04:8000'. If parsing the web_sockets.xml file produces an error
        (i.e. contains invalid xml) the UPD definitions will remain un-changed.
        """
        LOG.info('steward: Scan web_sockets.xml for UDP defs')
        # The try-except is here if we mess up editing the configuration file
        # while the program is running
        file_ = open(CURRENT_CONNECTIONS, 'w')
        file_.write("Found in xml file\n")
        file_.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
        try:
            tree = XML.parse('web_sockets.xml')
            self.udp_definitions.clear()
            for socket_ in tree.getroot():
                self.udp_definitions.add(socket_.text)
                file_.write(socket_.text + '\n')
                LOG.debug('steward: Found UPD def: {}'.format(socket_.text))
        except XML.ParseError:
            LOG.error('setward: Unable to parse web_sockets.xml')
        file_.write('\n')
        file_.close()
        LOG.debug('steward: Scan web_sockets.xml done')

    def _delete_dead_connections(self):
        """Delete any of the existing connections that are no longer alive"""
        for hostname_port, connection in self.udp_connections.items():
            if not connection.is_alive():
                LOG.info('steward: Connection {} was dead. Deleting '
                         'it'.format(hostname_port))
                del self.udp_connections[hostname_port]
                del DATA[hostname_port]

    def _delete_removed_connections(self, removed_connections):
        """Delete removed connections"""
        for hostname_port in removed_connections:
            LOG.info('steward: Deleting connection: {}'.format(hostname_port))
            sane = DATA[hostname_port]['sane_interval']
            self.udp_connections[hostname_port].stop()
            # The sane interval is used as wait time in the main run
            # loop and therefore there can be as much as a sane
            # interval delay before the thread has stopped
            time.sleep(2 * sane)
            if self.udp_connections[hostname_port].is_alive():
                LOG.error('steward: Connection {} will not shut down'
                          .format(hostname_port)
                          )

            del self.udp_connections[hostname_port]
            del DATA[hostname_port]

    def _add_new_connections(self, new_connections):
        """Add new connections and start them"""
        for hostname_port in new_connections:
            LOG.info('steward: Adding connection: {0}'.format(hostname_port))
            DATA[hostname_port] = {'data': None, 'codenames': None,
                             'sane_interval': None}
            self.udp_connections[hostname_port] = UDPConnection(hostname_port)
            self.udp_connections[hostname_port].start()


def main():
    """ Main method for the websocket server """
    LOG.info('main: Start')
    global LIVESOCKET  # pylint: disable=global-statement
    names = ['wss_hosts_defined', 'wss_hosts', 'wss_clients']
    LIVESOCKET = LiveSocket('websocketserver', names, sane_interval=1.0)
    LIVESOCKET.start()

    udp_steward = UDPConnectionSteward()
    udp_steward.start()

    # Uncomment these two to get log from twisted
    #import sys
    #log.startLogging(sys.stdout)
    # Create context factor with key and certificate
    context_factory = ssl.DefaultOpenSSLContextFactory(
        '/home/kenni/certs/fysik.dtu.dk.key',
        '/home/kenni/certs/fysik.dtu.dk-NEW.crt'
    )
    # Form the webserver factory
    factory = WebSocketServerFactory("wss://localhost:9001", debug=True)
    # Set the handler
    factory.protocol = CinfWebSocketHandler
    # Listen for incoming WebSocket connections: wss://localhost:9001
    listenWS(factory, context_factory)

    try:
        reactor.run()  # pylint: disable=E1101
        time.sleep(1)
        LOG.info('main: Keyboard interrupt, websocket reactor stopped')
        udp_steward.stop()
        time.sleep(1)
        LOG.info('main: UPD Steward stopped')
        LIVESOCKET.stop()
        time.sleep(1)
        LOG.info('main: Own livesocket stoppped')
    except Exception as exception_:
        LOG.exception(exception_)
        raise exception_

    LOG.info('main: Ended')
    raw_input('All stopped. Press enter to exit')

if __name__ == '__main__':
    main()
