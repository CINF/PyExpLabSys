# -*- coding: utf-8 -*-
"""General purpose data sockets"""

import threading
import SocketServer
import time
import json
import logging


LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
LOGGER.addHandler(logging.NullHandler())
BAD_CHARS = ['#', ',', ';', ':', ' ']
UNKNOWN_COMMAND = 'UNKNOWN_COMMMAND'
OLD_DATA = 'OLD_DATA'
DATA = {}


class DataUDPHandler(SocketServer.BaseRequestHandler):
    """Request handler for the data sockets"""

    def handle(self):
        """Return data corresponding to the request
        
        The handler understands the following commands:
        :param raw: Returns all values on the form: 'x1,y1;x2,y2' in the order
            the codenames was given to the DataSocket.__init__ method
        :param json: Return all values (list of points) as a json string
        :param raw_wn: (wn = with names) Return all values and their codenames
            on the form: codenam1:x1,y1;codename2:x2,y2
        :param json_wn: (wn = with names) Return the data dict as a json string
        :param codename#raw: Return the value for 'codename' on the form x,y
        :param codename#json: Return the value for 'codename' as a json string
        :param codenames_raw: Return the codenames on the form 'name1,name2'
        :param codenames_json: Return the list of codenames as a json string
        """
        command = self.request[0]
        self.port = self.server.server_address[1]
        socket = self.request[1]

        if command.count('#') == 1:
            data = self._single_value(command)
        else:
            data = self._all_values(command)

        socket.sendto(data, self.client_address)


    def _single_value(self, command):
        """Return a string for a single point"""
        name, command = command.split('#')
        if command == 'raw' and name in DATA[self.port]['data']:
            if self._old_data(name):
                out = OLD_DATA
            else:
                out = '{},{}'.format(*DATA[self.port]['data'][name])

        elif command == 'json' and name in DATA[self.port]['data']:
            if self._old_data(name):
                out = json.dumps(OLD_DATA)
            else:
                out = json.dumps(DATA[self.port]['data'][name])

        else:
            out = UNKNOWN_COMMAND

        return out

    def _all_values(self, command):
        """Return a string for all points or names"""
        # For a string of measurements in codenames order
        if command == 'raw':
            strings = []
            for codename in DATA[self.port]['codenames']:
                if self._old_data(codename):
                    string = OLD_DATA
                else:
                    string = '{},{}'.format(*DATA[self.port]['data'][codename])
                strings.append(string)
            out = ';'.join(strings)

        elif command == 'json':
            points = []
            for codename in DATA[self.port]['codenames']:                
                if self._old_data(codename):
                    data = OLD_DATA
                else:
                    data = DATA[self.port]['data'][codename]
                points.append(data)
            out = json.dumps(points)

        elif command == 'raw_wn':
            strings = []
            for codename in DATA[self.port]['codenames']:
                if self._old_data(codename):
                    string = '{}:{}'.format(codename, OLD_DATA)
                else:
                    string = '{}:{},{}'.format(
                        codename, *DATA[self.port]['data'][codename]
                        )
                strings.append(string)
            out = ';'.join(strings)

        elif command == 'json_wn':
            datacopy = dict(DATA[self.port]['data'])
            for codename in DATA[self.port]['codenames']:
                if self._old_data(codename):
                    datacopy[codename] = OLD_DATA
            out = json.dumps(datacopy)

        elif command == 'codenames_raw':
            out = ','.join(DATA[self.port]['codenames'])

        elif command == 'codenames_json':
            out = json.dumps(DATA[self.port]['codenames'])

        else:
            out = UNKNOWN_COMMAND

        return out

    def _old_data(self, code_name):
        """Check if the data for code_name has timed out"""
        now = time.time()
        if DATA[self.port]['type'] == 'date':
            timeout = DATA[self.port]['timeouts'].get(code_name)
            if timeout is not None:
                point_time = DATA[self.port]['data'][code_name][0]
                out = now - point_time > timeout
            else:
                out = False
        elif DATA[self.port]['type'] == 'data':
            out = False
        else:
            raise NotImplementedError

        return out


class DataSocket(threading.Thread):

    def __init__(self, code_names, port=9000, default_x=47, default_y=47):
        """Init data and UPD server

        :param code_names: List of codenames for the measurements. The names
            must be unique and cannot contain the characters: #,;: and SPACE
        :type code_names: list
        :param port: Network port to use for the socket (deafult 9000)
        :type port: int
        :param default_x: The x value the measurements are initiated with
        :type default_x: float
        :param default_y: The y value the measurements are initiated with
        :type default_y: float
        """
        LOGGER.debug('Initialize')
        # Init thread
        super(DataSocket, self).__init__()
        self.daemon = True
        # Init local data
        self.port = port
        # Check for existing servers on this port
        global DATA
        if port in DATA:
            message = 'A UDP server already exists on port: {}'.format(port)
            raise ValueError(message)
        # Prepare DATA
        DATA[port] = {'type': 'data', 'codenames': list(code_names),
                      'data': {}}
        for name in code_names:
            # Check for duplicates
            if code_names.count(name) > 1:
                message = 'Codenames must be unique; \'{}\' is present more '\
                    'than once'.format(name)
                raise ValueError(message)
            # Check for bad characters in the name
            for char in BAD_CHARS:
                if char in name:
                    message = 'The character \'{}\' is not allowed in the '\
                        'codenames'.format(char)
                    raise ValueError(message)
            # Init the point
            DATA[port]['data'][name] = (default_x, default_y)
        # Setup server
        self.server = SocketServer.UDPServer(('', port), DataUDPHandler)
        LOGGER.info('Initialized')

    def run(self):
        """Start the UPD socket server"""
        LOGGER.info('Start')
        self.server.serve_forever()
        LOGGER.info('Run ended')

    def stop(self):
        """Stop the UDP server"""
        LOGGER.debug('Stop requested')
        self.server.shutdown()
        # Wait 0.1 sec to prevent the interpreter to destroy the environment
        # before we are done
        time.sleep(0.1)
        # Delete the data, to allow forming another socket on this port
        del DATA[self.port]
        LOGGER.info('Stopped')

    def set_point(self, codename, point):
        """Set the current point for codename
        
        :param codename: Codename for the measurement whose 
        :type codename: str
        :param value: Current point as a tuple of 2 floats: (x, y)
        :type value: tuple
        """
        DATA[self.port]['data'][codename] = point
        LOGGER.debug('Point {} for \'{}\' set'.format(str(point), codename))


class DateDataSocket(threading.Thread):

    def __init__(self, code_names, port=9000, default_x=0, default_y=47,
                 timeouts=None):
        """Init data and UPD server

        :param code_names: List of codenames for the measurements. The names
            must be unique and cannot contain the characters: #,;: and SPACE
        :type code_names: list
        :param port: Network port to use for the socket (deafult 9000)
        :type port: int
        :param default_x: The x value the measurements are initiated with
        :type default_x: float
        :param default_y: The y value the measurements are initiated with
        :type default_y: float
        :param timeouts: The timeouts (in seconds as floats) the determines
            when the date data socket regards the data as being to old and
            reports that
        :type timeouts: Single float or list of floats, one for each codename
        """
        LOGGER.debug('Initialize')
        # Init thread
        super(DateDataSocket, self).__init__()
        self.daemon = True
        # Init local data
        self.port = port
        # Check for existing servers on this port
        global DATA
        if port in DATA:
            message = 'A UDP server already exists on port: {}'.format(port)
            raise ValueError(message)
        # Check and possibly convert timeout
        if hasattr(timeouts, '__len__'):
            if len(timeouts) != len(code_names):
                message = 'If a list of timeouts is supplied, it must have '\
                    'as many items as there are in code_names'
                raise ValueError(message)
            timeouts = list(timeouts)
        else:
            # If only a single value is given turn it into a list
            timeouts = [timeouts] * len(code_names)
        # Prepare DATA
        DATA[port] = {'type': 'date', 'codenames': list(code_names),
                      'data': {}, 'timeouts': {}}
        for name, timeout in zip(code_names, timeouts):
            # Check for duplicates
            if code_names.count(name) > 1:
                message = 'Codenames must be unique; \'{}\' is present more '\
                    'than once'.format(name)
                raise ValueError(message)
            # Check for bad characters in the name
            for char in BAD_CHARS:
                if char in name:
                    message = 'The character \'{}\' is not allowed in the '\
                        'codenames'.format(char)
                    raise ValueError(message)
            # Init the point
            DATA[port]['data'][name] = (default_x, default_y)
            DATA[port]['timeouts'][name] = timeout
        # Setup server
        self.server = SocketServer.UDPServer(('', port), DataUDPHandler)
        LOGGER.info('Initialized')

    def run(self):
        """Start the UPD socket server"""
        LOGGER.info('Start')
        self.server.serve_forever()
        LOGGER.info('Run ended')

    def stop(self):
        """Stop the UDP server"""
        LOGGER.debug('Stop requested')
        self.server.shutdown()
        # Wait 0.1 sec to prevent the interpreter to destroy the environment
        # before we are done
        time.sleep(0.1)
        # Delete the data, to allow forming another socket on this port
        del DATA[self.port]
        LOGGER.info('Stopped')

    def set_point_now(self, codename, value):
        """Set the current y-value for codename using the current time as x
        
        :param codename: Codename for the measurement whose 
        :type codename: str
        :param value: y-value
        :type value: float
        """
        self.set_point(codename, (time.time(), value))
        LOGGER.debug('Added time to value and called set_point')

    def set_point(self, codename, point):
        """Set the current point for codename
        
        :param codename: Codename for the measurement whose 
        :type codename: str
        :param value: Current point as a tuple of 2 floats: (x, y)
        :type value: tuple
        """
        DATA[self.port]['data'][codename] = point
        LOGGER.debug('Point {} for \'{}\' set'.format(str(point), codename))