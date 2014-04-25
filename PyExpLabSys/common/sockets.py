# -*- coding: utf-8 -*-
"""The sockets module contains various implementations of UDP socket servers
for transmission of data over the network. The different implementations aim to
be tailored to serve a specific purpose.

Presently the module contains only a date date socket server.

**Module variables:**

The modul contains a set of module variables used either as constants or as a
shared data storage between different instances of the socket servers. The
variables are the following:

.. autodata:: BAD_CHARS
.. autodata:: UNKNOWN_COMMAND
.. autodata:: OLD_DATA
.. autodata:: DATA

"""

import threading
import SocketServer
import time
import json
import logging


LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
LOGGER.addHandler(logging.NullHandler())
#: The list of characters that are not allowed in code names
BAD_CHARS = ['#', ',', ';', ':']
#: The string returned if an unknown command is sent to the socket
UNKNOWN_COMMAND = 'UNKNOWN_COMMMAND'
#: The string used to indicate old or obsoleted data
OLD_DATA = 'OLD_DATA'
#:The variable used to contain all the data.
#:
#:The format of the DATA variable is the following. The DATA variable is a
#:dict, where each key is an integer port number and the value is the data for
#:the socket server on that port. The data for each individual socket server is
#:always a dict, but the contained values will depend on which kind of socket
#:server it is.
#:
#:For a :class:`DateDataSocket` the dict will resemble this example:
#:
#: .. code-block:: python
#:
#:  {'type': 'date', 'codenames': ['ex1', 'ex2'],
#:   'timeouts': {'ex1': 3, 'ex2': 0.7},
#:   'data': {'ex1': [1234.5, 47.0], 'ex2':[1234.2, 42.0]}
#:  }
#:
DATA = {}


class DataUDPHandler(SocketServer.BaseRequestHandler):
    """Request handler for the :class:`.DateDataSocket` and
    :class:`.DateDataSocket` sockets
    """

    def handle(self):
        """Return data corresponding to the request
        
        The handler understands the following commands:

        :param raw: Returns all values on the form ``x1,y1;x2,y2`` in the
            order the codenames was given to the
            :meth:`.DateDataSocket.__init__` or :meth:`.DataSocket.__init__`
            method
        :param json: Return all values as a list of points (which in themselves
            are lists) e.g: ``[[x1, y1], [x2, y2]]``), contained in a
            :py:mod:`json` string. The order is the same as in ``raw``.
        :param raw_wn: (wn = with names) Same as raw but with names, e.g.
            ``codenam1:x1,y1;codename2:x2,y2``. The order is the same as in
            ``raw``.
        :param json_wn: (wn = with names) Return all data as a
            :py:class:`dict` contained in a :py:mod:`json` string. In the dict
            the keys are the codenames.
        :param codename#raw: Return the value for ``codename`` on the form
            ``x,y``
        :param codename#json: Return the value for ``codename`` as a list (e.g
            ``[x1, y1]``) contained in a :py:mod:`json` string
        :param codenames_raw: Return the list of codenames on the form
            ``name1,name2``
        :param codenames_json: Return a list of the codenames contained in a
            :py:mod:`json` string
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
        """Return a string for a single point

        :param command: Complete command string
        :type command: str
        """
        name, command = command.split('#')
        # Return as raw string
        if command == 'raw' and name in DATA[self.port]['data']:
            if self._old_data(name):
                out = OLD_DATA
            else:
                out = '{},{}'.format(*DATA[self.port]['data'][name])
        # Return a json encoded string
        elif command == 'json' and name in DATA[self.port]['data']:
            if self._old_data(name):
                out = json.dumps(OLD_DATA)
            else:
                out = json.dumps(DATA[self.port]['data'][name])
        # The command is unknown
        else:
            out = UNKNOWN_COMMAND

        return out

    def _all_values(self, command):
        """Return a string for all points or names

        :param command: Command string
        :type command: str
        """
        # Return a raw string with all measurements in codenames order
        if command == 'raw':
            strings = []
            for codename in DATA[self.port]['codenames']:
                if self._old_data(codename):
                    string = OLD_DATA
                else:
                    string = '{},{}'.format(*DATA[self.port]['data'][codename])
                strings.append(string)
            out = ';'.join(strings)
        # Return a json encoded string with list of all measurements
        elif command == 'json':
            points = []
            for codename in DATA[self.port]['codenames']:                
                if self._old_data(codename):
                    data = OLD_DATA
                else:
                    data = DATA[self.port]['data'][codename]
                points.append(data)
            out = json.dumps(points)
        # Return a raw string with all measurements in codenames order
        # including names
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
        # Return a copy of the data dict encoded as a json string
        elif command == 'json_wn':
            datacopy = dict(DATA[self.port]['data'])
            for codename in DATA[self.port]['codenames']:
                if self._old_data(codename):
                    datacopy[codename] = OLD_DATA
            out = json.dumps(datacopy)
        # Return all codesnames in a raw string
        elif command == 'codenames_raw':
            out = ','.join(DATA[self.port]['codenames'])
        # Return a list with all codenames encoded as a json string
        elif command == 'codenames_json':
            out = json.dumps(DATA[self.port]['codenames'])
        # The command is not known
        else:
            out = UNKNOWN_COMMAND

        return out

    def _old_data(self, code_name):
        """Check if the data for code_name has timed out"""
        now = time.time()
        if DATA[self.port]['type'] == 'date':
            timeout = DATA[self.port]['timeouts'].get(code_name)
            if timeout is None:
                out = False
            else:
                point_time = DATA[self.port]['data'][code_name][0]
                out = now - point_time > timeout
        elif DATA[self.port]['type'] == 'data':
            timeout = DATA[self.port]['timeouts'].get(code_name)
            if timeout is None:
                out = False
            else:
                timestamp = DATA[self.port]['timestamps'][code_name]
                out = now - timestamp > timeout
        else:
            message = 'Checking for timeout is not yet implemented for type '\
                '\'{}\''.format(DATA[self.port]['type'])
            raise NotImplementedError(message)

        return out


class LiveUDPHandler(SocketServer.BaseRequestHandler):
    """Request handler for the :class:`.DateDataSocket` and
    :class:`.DateDataSocket` sockets
    """

    def handle(self):
        """Return data corresponding to the request

        All data is returned as json strings even though the command names does
        not indicate it.

        The handler understands the following commands:

        :param data: Return all values as a list of points (which in themselves
            are lists) e.g: ``[[x1, y1], [x2, y2]]``), contained in a
            :py:mod:`json` string. The order of the points is the same order
            the codenames was given to the :meth:`.LiveSocket.__init__` method
            in and is returned by the ``codenames`` command.
        :param codenames: Return a list of the codenames contained in a
            :py:mod:`json` string
        :param sane_interval: Return the sane interval with which new data can
            be expected to be available
        """
        command = self.request[0]
        self.port = self.server.server_address[1]
        socket = self.request[1]

        if command == 'data':
            points = []
            for codename in DATA[self.port]['codenames']:
                points.append(DATA[self.port]['data'][codename])
            data = json.dumps(points)
        elif command == 'codenames':
            data = json.dumps(DATA[self.port]['codenames'])
        elif command == 'sane_interval':
            data = json.dumps(DATA[self.port]['sane_interval'])
        else:
            data = UNKNOWN_COMMAND

        socket.sendto(data, self.client_address)


class CommonDataSocket(threading.Thread):
    """Abstract class that implements common data socket functionality.
    
    This common class is responsible for:

    * Initializing the thread
    * Checking the inputs
    * Initilizing DATA with common attributes
    """

    def __init__(self, codenames, port, default_x, default_y, timeouts,
                 init_timeouts=True, handler_class=DataUDPHandler):
        """For parameter description of ``codenames``, ``port``, ``default_x``,
        ``default_y`` and ``timeouts`` see :meth:`.DataSocket.__init__` or
        :meth:`.DateDataSocket.__init__`.

        :param init_timeouts: Whether timeouts should be instantiated in the
            DATA
        :type init_timeouts: bool
        :param handler_class: The UDP handler to use in the server
        :type DataUDPHandler: Sub-class of
            :python:`SocketServer.BaseRequestHandler`
        """
        LOGGER.debug('CDS: Initialize')
        # Init thread
        super(CommonDataSocket, self).__init__()
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
            if len(timeouts) != len(codenames):
                message = 'If a list of timeouts is supplied, it must have '\
                    'as many items as there are in codenames'
                raise ValueError(message)
            timeouts = list(timeouts)
        else:
            # If only a single value is given turn it into a list
            timeouts = [timeouts] * len(codenames)

        # Prepare DATA
        DATA[port] = {'codenames': list(codenames), 'data': {}}
        if init_timeouts:
            DATA[port]['timeouts'] = {}
        for name, timeout in zip(codenames, timeouts):
            # Check for duplicates
            if codenames.count(name) > 1:
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
            if init_timeouts:
                DATA[port]['timeouts'][name] = timeout

        # Setup server
        self.server = SocketServer.UDPServer(('', port), handler_class)
        LOGGER.info('CDS: Initialized')

    def run(self):
        """Start the UPD socket server"""
        LOGGER.info('CDS: Start')
        self.server.serve_forever()
        LOGGER.info('CDS: Run ended')

    def stop(self):
        """Stop the UDP server

        .. note:: Closing the server **and** deleting the
            :class:`.DateDataSocket` socket instance is necessary to free up the
            port for other usage
        """
        LOGGER.debug('CDS: Stop requested')
        self.server.shutdown()
        # Wait 0.1 sec to prevent the interpreter from destroying the
        # environment before we are done
        time.sleep(0.1)
        # Delete the data, to allow forming another socket on this port
        del DATA[self.port]
        LOGGER.info('CDS: Stopped')


class DataSocket(CommonDataSocket):

    def __init__(self, codenames, port=9010, default_x=47, default_y=47,
                 timeouts=None):
        """Init data and UPD server

        :param codenames: List of codenames for the measurements. The names
            must be unique and cannot contain the characters: #,;: and SPACE
        :type codenames: list
        :param port: Network port to use for the socket (deafult 9010)
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
        LOGGER.debug('DS: Initialize')
        # Run super init to initialize thread, check input and initialize data
        super(DataSocket, self).__init__(
            codenames, port=port, default_x=default_x, default_y=default_y,
            timeouts=timeouts
        )
        DATA[port]['type'] = 'data'
        # Init timestamps
        DATA[port]['timestamps'] = {}
        for name in codenames:
            DATA[port]['timestamps'][name] = 0.0
        LOGGER.info('DS: Initialized')

    def set_point(self, codename, point, timestamp=None):
        """Set the current point for codename
        
        :param codename: Name for the measurement whose current point should be
            set
        :type codename: str
        :param value: Current point as a list or tuple of 2 floats: [x, y]
        :type value: list or tuble
        :param timestamp: A unix timestamp that indicates when the point was
            measured. If it is not set, it is assumed to be now. This value is
            used to evaluate if the point is new enough if timeouts are set.
        :type timestamp: float
        """
        DATA[self.port]['data'][codename] = tuple(point)
        if timestamp is None:
            timestamp = time.time()
        DATA[self.port]['timestamps'][codename] = timestamp
        LOGGER.debug('DS: Point {} for \'{}\' set'.format(tuple(point),
                                                          codename))


class DateDataSocket(CommonDataSocket):
    """This class implements a UDP socket for serving data as function of time.
    The UDP server uses the :class:`.DataUDPHandler` class to handle the UDP
    requests. The the commands that can be used with this socket is documented
    in that class.

    The main features of the data data logger is:

    * **Simple single method usage.** After the class is instantiated, a single
      call to :meth:`.DateDataSocket.set_point` or
      :meth:`.DateDataSocket.set_point_now` is all that is needed to make a
      point available via the socket.
    * **Timeout safety to prevent serving obsolete data.** The class can be
      instantiated with a timeout for each measurement type. If the available
      point is too old an error message will be served.
    """

    def __init__(self, codenames, port=9000, default_x=0, default_y=47,
                 timeouts=None):
        """Init data and UPD server

        :param codenames: List of codenames for the measurements. The names
            must be unique and cannot contain the characters: ``#,;:``
        :type codenames: list
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
        # Run super init to initialize thread, check input and initialize data
        super(DateDataSocket, self).__init__(
            codenames, port=port, default_x=default_x, default_y = default_y,
            timeouts=timeouts
        )
        # Set the type
        DATA[port]['type'] = 'date'
        LOGGER.info('Initialized')

    def set_point_now(self, codename, value):
        """Set the current y-value for codename using the current time as x
        
        :param codename: Name for the measurement whose current value should be
            set
        :type codename: str
        :param value: y-value
        :type value: float
        """
        self.set_point(codename, (time.time(), value))
        LOGGER.debug('Added time to value and called set_point')

    def set_point(self, codename, point):
        """Set the current point for codename
        
        :param codename: Name for the measurement whose current point should be
            set
        :type codename: str
        :param point: Current point as a list (or tuple) of 2 floats: [x, y]
        :type point: list or tuple
        """
        DATA[self.port]['data'][codename] = tuple(point)
        LOGGER.debug('Point {} for \'{}\' set'.format(tuple(point), codename))


class LiveSocket(CommonDataSocket):
    """This class implements a Live Socket"""

    def __init__(self, codenames, sane_interval, port=8000,
                 default_x=0, default_y=47):

        LOGGER.info('LS: Initilize')
        super(LiveSocket, self).__init__(
            codenames, port, default_x, default_y, None, init_timeouts=False,
            handler_class=LiveUDPHandler
        )
        # Set the type and the the sane_interval
        DATA[port]['type'] = 'live'
        DATA[port]['sane_interval'] = sane_interval

        # Initialize the last served data
        DATA[port]['last_served'] = {}
        for codename in codenames:
            DATA[port]['last_served'][codename] = (default_x, default_y)
        LOGGER.info('LS: Initilized')

    def set_point_now(self, codename, value):
        """Set the current y-value for codename using the current time as x
        
        :param codename: Name for the measurement whose current value should be
            set
        :type codename: str
        :param value: y-value
        :type value: float
        """
        self.set_point(codename, (time.time(), value))
        LOGGER.debug('LS: Added time to value and called set_point')

    def set_point(self, codename, point):
        """Set the current point for codename
        
        :param codename: Name for the measurement whose current point should be
            set
        :type codename: str
        :param point: Current point as a list (or tuple) of 2 floats: [x, y]
        :type point: list or tuple
        """
        if not codename in DATA[self.port]['codenames']:
            message = 'Codename \'{}\' not recognized. Use one of: {}'.format(
                codename,
                DATA[self.port]['codenames']
            )
            raise ValueError(message)
        DATA[self.port]['data'][codename] = tuple(point)
        LOGGER.debug('LS: Point {} for \'{}\' set'.format(tuple(point),
                                                          codename))


class RecieveUDPHandler(SocketServer.BaseRequestHandler):
    """This class handles the UDP requests for the :class:`.DataRecieveSocket`
    """

    def handle(self):
        """Set data corresponding to the request

        The handler understands the following commands:
        :param json_wn: Json with names
        :param raw_wn_float: Raw with names float
        :param raw_wn_str: Raw with names string
        """
        request = self.request[0]
        self.port = self.server.server_address[1]
        socket = self.request[1]

        if request.count('#') != 1:
            return_value = UNKNOWN_COMMAND
        else:
            command, data = request.split('#')
            if command == 'json_wn':
                return_value = self._json_with_names(data)
            elif command == 'raw_wn_float':
                return_value = self._raw_with_names(float, data)
            elif command == 'raw_wn_str':
                return_value = self._raw_with_names(str, data)
            else:
                return_value = UNKNOWN_COMMAND

        socket.sendto(return_value, self.client_address)

    def _raw_with_names(self, data_type, data):
        """Add raw data to the queue, cast type according to data_type"""
        # parse name, value pairs, cast and add
        pass

    def _json_with_names(self, data):
        """Add json encoded data to the data queue"""
        DATA[self.port]['queue'].put(json.loads(data))


class DataReceiveSocket(threading.Thread):
    """This class implements a data recieve socket and provides options for
    enqueuing, calling back or doing nothing on reciept of data
    """

    def __init__(self, codenames, port=8500):
        # Init thread
        super(DataReceiveSocket, self).__init__()
        self.daemon = True
        # Init local data
        self.port = port

        





