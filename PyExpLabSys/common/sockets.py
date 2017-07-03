# pylint: disable=too-many-arguments,too-many-lines,import-error
# -*- coding: utf-8 -*-
"""The sockets module contains various implementations of UDP socket servers
(at present 4 in total) for transmission of data over the network. The
different implementations are tailored for a specific purposes, as described below.

In general, there is a distinction in the naming of the different socket server
implementation between **push** socket servers, that you can push data to, and
**pull** socket servers, that you can pull data from.

Presently the module contains the following socket servers:

 * **DateDataPullSocket** (:class:`.DateDataPullSocket`) This socket server is
   used to make continuous data
   (i.e. one-value data as function of time) available on the network. It
   identifies different data channels by codenames and has a timeout
   functionality to prevent serving old data to the client.
 * **DataPullSocket** (:class:`.DataPullSocket`) This socket is similar to the
   date data server, but is
   used to make x, y type data available on the network. It identifies
   different data channel by codenames and has timeout functionality to
   prevent serving old data.
 * **DataPushSocket** (:class:`.DataPushSocket`) This socket is used to recieve
   data from the network. The
   data is received in dictionary form and it identifies the data channels by
   codenames (keys) in the dictionaries. It will save the last point, and the
   last value for each codename. It also has the option to, for each received
   data set, to put them in a queue (that the user can then empty) or to call
   a callback function with the received data as en argument.
 * **LiveSocket** (:class:`.LiveSocket`) This socket is used only for serving
   data to the live socket server. It also is not actually a socket server
   like the others, but it has a similar interface.

.. note:: The module variable :data:`.DATA` is a dict shared for all socket
 servers started from this module. It contains all the data, queues, settings
 etc. It can be a good place to look if, to get a behind the scenes look at
 what is happening.
"""

from __future__ import print_function, unicode_literals

import sys
import threading
import socket
try:
    import SocketServer
except ImportError:
    # SocketServer was renamed in Python3
    import socketserver as SocketServer
import time
import json
try:
    import Queue
except ImportError:
    # Queue was renamed to queue in Python 3
    import queue as Queue
import logging
import six
from .utilities import call_spec_string
from .system_status import SystemStatus
from ..settings import Settings
from .supported_versions import python2_and_3

# Instantiate module logger
LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
LOGGER.addHandler(logging.NullHandler())

# Instantiate a global system status object
SYSTEM_STATUS = SystemStatus()

# Indicate Python 2/3
python2_and_3(__file__)

# Instantiate settings object
SETTINGS = Settings()
LOGGER.debug("Settings loaded with the following values: %s", SETTINGS.settings)


def bool_translate(string):
    """Returns boolean value from strings 'True' or 'False'"""
    if str(string) not in ['True', 'False']:
        message = 'Cannot translate the string \'{}\' to a boolean. Only the '\
            'strings \'True\' or \'False\' are allowed'.format(string)
        raise ValueError(message)
    return True if str(string) == 'True' else False


def socket_server_status():
    """Returns the status of all socket servers

    Returns:
        dict: Dict with port to status dict mapping. The status dict has the following keys:
            name, type, status (with str values) and since_last_activity with float value.
    """
    status_dict = {}
    for port, data in DATA.items():
        if data['activity']['check_activity']:
            since_last_activity = time.time() -\
                data['activity']['last_activity']
            if since_last_activity < data['activity']['activity_timeout']:
                status = 'OK'
            else:
                status = 'INACTIVE'
        else:
            status = 'DISABLED'
            since_last_activity = None

        status_dict[port] = {
            'name': data['name'],
            'type': data['type'],
            'status': status,
            'since_last_activity': since_last_activity
        }
    return status_dict


PULLUHLOG = logging.getLogger(__name__ + '.PullUDPHandler')
PULLUHLOG.addHandler(logging.NullHandler())
class PullUDPHandler(SocketServer.BaseRequestHandler):
    """Request handler for the :class:`.DateDataPullSocket` and
    :class:`.DateDataPullSocket` socket servers. The commands this request
    handler understands are documented in the :meth:`.handle` method.
    """

    def handle(self):
        """Returns data corresponding to the request

        The handler understands the following commands:

        **COMMANDS**

         * **raw** (*str*): Returns all values on the form ``x1,y1;x2,y2`` in
           the order the codenames was given to the
           :meth:`.DateDataPullSocket.__init__` or
           :meth:`.DataPullSocket.__init__` method
         * **json** (*str*): Return all values as a list of points (which in
           themselves are lists) e.g: ``[[x1, y1], [x2, y2]]``), contained in a
           :py:mod:`json` string. The order is the same as in ``raw``.
         * **raw_wn** (*str*): (wn = with names) Same as raw but with names,
           e.g. ``codenam1:x1,y1;codename2:x2,y2``. The order is the same as in
           ``raw``.
         * **json_wn** (*str*): (wn = with names) Return all data as a
           :py:class:`dict` contained in a :py:mod:`json` string. In the dict
           the keys are the codenames.
         * **codename#raw** (*str*): Return the value for ``codename`` on the
           form ``x,y``
         * **codename#json** (*str*): Return the value for ``codename`` as a
           list (e.g ``[x1, y1]``) contained in a :py:mod:`json` string
         * **codenames_raw** (*str*): Return the list of codenames on the form
           ``name1,name2``
         * **codenames_json** (*str*): Return a list of the codenames contained
           in a :py:mod:`json` string
         * **name** (*str*): Return the name of the socket server
         * **status** (*str*): Return the system status and status for all
           socket servers.
        """
        command = self.request[0].decode('ascii')
        # pylint: disable=attribute-defined-outside-init
        self.port = self.server.server_address[1]
        sock = self.request[1]
        PULLUHLOG.debug('Request \'%s\' received from %s on port %s',
                        command, self.client_address, self.port)

        if command.count('#') == 1:
            data = self._single_value(command)
        else:
            # The "name" and "status" commands are also handled here
            data = self._all_values(command)

        sock.sendto(data.encode('ascii'), self.client_address)
        PULLUHLOG.debug('Sent back \'%s\' to %s', data, self.client_address)

    def _single_value(self, command):
        """Returns a string for a single point

        Args:
            command (str): Complete command

        Returns:
            str: The data as a string (or an error) to be sent back
        """
        PULLUHLOG.debug('Parsing single value command: %s', command)
        name, command = command.split('#')
        # Return as raw string
        if command == 'raw' and name in DATA[self.port]['data']:
            if self._old_data(name):
                out = OLD_DATA
            else:
                out = '{},{}'.format(*DATA[self.port]['data'][name])

        elif command == 'json' and name in DATA[self.port]['data']:
            if self._old_data(name):
                out = six.text_type(json.dumps(OLD_DATA))
            else:
                out = six.text_type(json.dumps(DATA[self.port]['data'][name]))
        # The command is unknown
        else:
            out = UNKNOWN_COMMAND

        return out

    # pylint: disable=too-many-branches
    def _all_values(self, command):
        """Returns a string for all points or names

        Args:
            command (str): Complete command

        Returns:
            str: The data as a string (or an error) to be sent back
        """
        PULLUHLOG.debug('Parsing all-values command: %s', command)
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
            out = six.text_type(json.dumps(points))
        # Return a raw string with all measurements in codenames order including names
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
            out = six.text_type(json.dumps(datacopy))
        # Return all codesnames in a raw string
        elif command == 'codenames_raw':
            out = ','.join(DATA[self.port]['codenames'])
        # Return a list with all codenames encoded as a json string
        elif command == 'codenames_json':
            out = six.text_type(json.dumps(DATA[self.port]['codenames']))
        # Return the socket server name
        elif command == 'name':
            out = DATA[self.port]['name']
        # Return status of system and all socket servers
        elif command == 'status':
            out = six.text_type(json.dumps({
                'system_status': SYSTEM_STATUS.complete_status(),
                'socket_server_status': socket_server_status()
            }))
        # The command is not known
        else:
            out = UNKNOWN_COMMAND

        return out

    def _old_data(self, codename):
        """Checks if the data for codename has timed out

        Args:
            codename (str): The codename whose data should be checked for
                timeout

        Returns:
            bool: Whether the data is too old or not
        """
        PULLUHLOG.debug('Check if data for \'%s\' is too old', codename)
        now = time.time()
        if DATA[self.port]['type'] == 'date':
            timeout = DATA[self.port]['timeouts'].get(codename)
            if timeout is None:
                out = False
            else:
                point_time = DATA[self.port]['data'][codename][0]
                out = now - point_time > timeout
        elif DATA[self.port]['type'] == 'data':
            timeout = DATA[self.port]['timeouts'].get(codename)
            if timeout is None:
                out = False
            else:
                timestamp = DATA[self.port]['timestamps'][codename]
                out = now - timestamp > timeout
        else:
            message = 'Checking for timeout is not yet implemented for type '\
                '\'{}\''.format(DATA[self.port]['type'])
            PULLUHLOG.error(message)
            raise NotImplementedError(message)

        return out


CDPULLSLOG = logging.getLogger(__name__ + '.CommonDataPullSocket')
CDPULLSLOG.addHandler(logging.NullHandler())
class CommonDataPullSocket(threading.Thread):
    """Abstract class that implements common data pull socket functionality.

    This common class is responsible for:

     * Initializing the thread
     * Checking the inputs
     * Starting the socket server with the correct handler
     * Initializing DATA with common attributes
    """

    # pylint: disable=too-many-branches
    def __init__(self, name, codenames, port, default_x, default_y, timeouts,
                 check_activity, activity_timeout, init_timeouts=True,
                 handler_class=PullUDPHandler):
        """Initializes internal variables and data structure in the
        :data:`.DATA` module variable

        Args:
            name (str): The name of the DataPullSocket server. Used for
                identification and therefore should contain enough information
                about location and purpose to unambiguously identify the socket
                server. E.g:
                ``'DataPullSocket with data from giant laser on the moon'``
            codenames (list): List of codenames for the measurements. The names
                must be unique and cannot contain the characters: ``#,;:`` and
                SPACE
            port (int): Network port to use for the socket (deafult 9010)
            default_x (float): The x value the measurements are initiated with
            default_y (float): The y value the measurements are initiated with
            timeouts (float or list of floats): The timeouts (in seconds as
                floats) the determines when the date data socket regards the
                data as being to old and reports that. If a list of timeouts is
                supplied there must be one value for each codename and in the
                same order.
            init_timeouts (bool): Whether timeouts should be instantiated in
                the :data:`.DATA` module variable
            handler_class (Sub-class of SocketServer.BaseRequestHandler): The
                UDP handler to use in the server
            check_activity (bool): Whether the socket server should monitor
                activity. What detemines activity is described in the derived
                socket servers.
            activity_timeout (float or int): The timespan in seconds which
                constitutes in-activity
        """
        CDPULLSLOG.info('Initialize with: %s', call_spec_string())
        # Init thread
        super(CommonDataPullSocket, self).__init__()
        self.daemon = True
        # Init local data
        self.port = port

        # Check for existing servers on this port
        if port in DATA:
            message = 'A UDP server already exists on port: {}'.format(port)
            CDPULLSLOG.error(message)
            raise ValueError(message)
        # Check and possibly convert timeout
        if hasattr(timeouts, '__len__'):
            if len(timeouts) != len(codenames):
                message = 'If a list of timeouts is supplied, it must have '\
                    'as many items as there are in codenames'
                CDPULLSLOG.error(message)
                raise ValueError(message)
            timeouts = list(timeouts)
        else:
            # If only a single value is given turn it into a list
            timeouts = [timeouts] * len(codenames)

        # Prepare DATA
        DATA[port] = {
            'codenames': list(codenames),
            'data': {},
            'name': name,
            'activity': {
                'check_activity': check_activity,
                'activity_timeout': activity_timeout,
                'last_activity': time.time()
            }
        }
        if init_timeouts:
            DATA[port]['timeouts'] = {}
        for name, timeout in zip(codenames, timeouts):
            # Check for duplicates
            if codenames.count(name) > 1:
                message = 'Codenames must be unique; \'{}\' is present more '\
                    'than once'.format(name)
                CDPULLSLOG.error(message)
                raise ValueError(message)
            # Check for bad characters in the name
            for char in BAD_CHARS:
                if char in name:
                    message = 'The character \'{}\' is not allowed in the '\
                        'codenames'.format(char)
                    CDPULLSLOG.error(message)
                    raise ValueError(message)
            # Init the point
            DATA[port]['data'][name] = (default_x, default_y)
            if init_timeouts:
                DATA[port]['timeouts'][name] = timeout

        # Setup server
        try:
            self.server = SocketServer.UDPServer(('', port), handler_class)
        except socket.error as error:
            if error.errno == 98:
                # See custom exception message to understand this
                CDPULLSLOG.error('Port \'%s\' still reserved', port)
                raise PortStillReserved()
            else:
                raise error
        CDPULLSLOG.debug('Initialized')

    def run(self):
        """Starts the UPD socket server"""
        CDPULLSLOG.info('Run')
        self.server.serve_forever()
        CDPULLSLOG.info('Run ended')

    def stop(self):
        """Stops the UDP server

        .. note:: Closing the server **and** deleting the socket server
                instance is necessary to free up the port for other usage
        """
        CDPULLSLOG.debug('Stop requested')
        self.server.shutdown()
        # Wait 0.1 sec to prevent the interpreter from destroying the
        # environment before we are done if this is the last thread
        time.sleep(0.1)
        # Delete the data, to allow forming another socket on this port
        #print(DATA)
        del DATA[self.port]
        #print(DATA)
        CDPULLSLOG.info('Stopped')

    def poke(self):
        """Pokes the socket server to let it know that there is activity"""
        if DATA[self.port]['activity']['check_activity']:
            DATA[self.port]['activity']['last_activity'] = time.time()


DPULLSLOG = logging.getLogger(__name__ + '.DataPullSocket')
DPULLSLOG.addHandler(logging.NullHandler())
class DataPullSocket(CommonDataPullSocket):
    """This class implements a UDP socket server for serving x, y type data.
    The UDP server uses the :class:`.PullUDPHandler` class to handle
    the UDP requests. The commands that can be used with this socket server are
    documented in the :meth:`.PullUDPHandler.handle()` method.
    """

    def __init__(self, name, codenames, port=9010, default_x=0.0,
                 default_y=0.0, timeouts=None, check_activity=True,
                 activity_timeout=900, poke_on_set=True):
        """Initializes internal variables and UPD server

        For parameter description of ``name``, ``codenames``, ``port``,
        ``default_x``, ``default_y``, ``timeouts``, ``check_activity`` and
        ``activity_timeout`` see :meth:`.CommonDataPullSocket.__init__`.

        Args:
            poke_on_set (bool): Whether to poke the socket server when a point
                is set, to let it know there is activity
        """
        DPULLSLOG.info('Initialize with: %s', call_spec_string())
        # Run super init to initialize thread, check input and initialize data
        super(DataPullSocket, self).__init__(
            name, codenames, port=port, default_x=default_x,
            default_y=default_y, timeouts=timeouts,
            check_activity=check_activity, activity_timeout=activity_timeout
        )
        DATA[port]['type'] = 'data'
        # Init timestamps
        DATA[port]['timestamps'] = {}
        for name in codenames:
            DATA[port]['timestamps'][name] = 0.0
        DPULLSLOG.debug('Initialized')
        # Init poke_on_set
        self.poke_on_set = poke_on_set

    def set_point(self, codename, point, timestamp=None):
        """Sets the current point for codename

        Args:
            codename (str): Name for the measurement whose current point should
                be set
            value (iterable): Current point as a list or tuple of 2 floats:
                [x, y]
            timestamp (float): A unix timestamp that indicates when the point
                was measured. If it is not set, it is assumed to be now. This
                value is used to evaluate if the point is new enough if
                timeouts are set.
        """
        DATA[self.port]['data'][codename] = tuple(point)
        if timestamp is None:
            timestamp = time.time()
        DATA[self.port]['timestamps'][codename] = timestamp
        DPULLSLOG.debug('Point %s for \'%s\' set', tuple(point), codename)
        # Poke if required
        if DATA[self.port]['activity']['check_activity'] and self.poke_on_set:
            self.poke()


DDPULLSLOG = logging.getLogger(__name__ + '.DateDataPullSocket')
DDPULLSLOG.addHandler(logging.NullHandler())
class DateDataPullSocket(CommonDataPullSocket):
    """This class implements a UDP socket server for serving data as a function
    of time. The UDP server uses the :class:`.PullUDPHandler` class to handle
    the UDP requests. The commands that can be used with this socket server are
    documented in the :meth:`.PullUDPHandler.handle()` method.

    """

    def __init__(self, name, codenames, port=9000, default_x=0.0,
                 default_y=0.0, timeouts=None, check_activity=True,
                 activity_timeout=900, poke_on_set=True):
        """Init internal variavles and UPD server

        For parameter description of ``name``, ``codenames``, ``port``,
        ``default_x``, ``default_y``, ``timeouts``, ``check_activity`` and
        ``activity_timeout`` see :meth:`.CommonDataPullSocket.__init__`.

        Args:
            poke_on_set (bool): Whether to poke the socket server when a point
                is set, to let it know there is activity
        """
        DDPULLSLOG.info('Initialize with: %s', call_spec_string())
        # Run super init to initialize thread, check input and initialize data
        super(DateDataPullSocket, self).__init__(
            name, codenames, port=port, default_x=default_x,
            default_y=default_y, timeouts=timeouts,
            check_activity=check_activity, activity_timeout=activity_timeout
        )
        # Set the type
        DATA[port]['type'] = 'date'
        DDPULLSLOG.debug('Initialized')
        # Init poke_on_set
        self.poke_on_set = poke_on_set

    def set_point_now(self, codename, value):
        """Sets the current y-value for codename using the current time as x

        Args:
            codename (str): Name for the measurement whose current value should
                be set
            value (float): y-value
        """
        self.set_point(codename, (time.time(), value))
        DDPULLSLOG.debug('Added time to value and called set_point')

    def set_point(self, codename, point):
        """Sets the current point for codename

        Args:
            codename (str): Name for the measurement whose current point should
                be set
            point (iterable): Current point as a list (or tuple) of 2 floats:
                [x, y]
        """
        DATA[self.port]['data'][codename] = tuple(point)
        DDPULLSLOG.debug('Point %s for \'%s\' set', tuple(point), codename)
        # Poke if required
        if DATA[self.port]['activity']['check_activity'] and self.poke_on_set:
            self.poke()


PUSHUHLOG = logging.getLogger(__name__ + '.PushUDPHandler')
PUSHUHLOG.addHandler(logging.NullHandler())
class PushUDPHandler(SocketServer.BaseRequestHandler):
    """This class handles the UDP requests for the :class:`.DataPushSocket`"""

    def handle(self):
        """Sets data corresponding to the request

        The handler understands the following commands:

        **COMMANDS**

         * **json_wn#data** (*str*): Json with names. The data should be a
           JSON encoded dict with codename->value content. A complete command
           could look like:\n
           ``'json_wn#{"greeting": "Live long and prosper", "number": 47}'``
         * **raw_wn#data** (*str*): Raw with names. The data should be a string
           with data on the following format:
           ``codename1:type:data;codename2:type:data;...`` where ``type`` is
           the type of the data and can be one of ``'int'``, ``'float'``,
           ``'str'`` and ``'bool'``. NOTE; that neither the names or any data
           strings can contain any of the characters in :data:`.BAD_CHARS`. The
           ``data`` is a comma separated list of data items of that type. If
           there is more than one, they will be put in a list. An example of a
           complete raw_wn string could look like:\n
           ``'raw_wn#greeting:str:Live long and prosper;numbers:int:47,42'``
         * **name** (*str*): Return the name of the PushSocket server
         * **status** (*str*): Return the system status and status for all
           socket servers.
         * **commands** (*str*): Return a json encoded list of commands. The returns value is
           is prefixed with :data:`.PUSH_RET` and '#' so e.g. 'RET#actual_date'
        """
        request = self.request[0].decode('ascii')
        PUSHUHLOG.debug('Request \'%s\'received', request)
        # pylint: disable=attribute-defined-outside-init
        self.port = self.server.server_address[1]
        sock = self.request[1]

        # Parse the request and call the appropriate helper methods
        if request == 'name':
            return_value = '{}#{}'.format(PUSH_RET, DATA[self.port]['name'])
        elif request == 'commands':
            commands = ['json_wn#', 'raw_wn#', 'name', 'status', 'commands']
            return_value = '{}#{}'.format(PUSH_RET, json.dumps(commands))
        elif request == 'status':
            return_value = six.text_type(json.dumps({
                'system_status': SYSTEM_STATUS.complete_status(),
                'socket_server_status': socket_server_status()
            }))
        elif request.count('#') != 1:
            return_value = '{}#{}'.format(PUSH_ERROR, UNKNOWN_COMMAND)
        else:
            # Parse a command on the form command#data
            command, data = request.split('#')
            try:
                if command == 'json_wn':
                    return_value = self._json_with_names(data)
                elif command == 'raw_wn':
                    return_value = self._raw_with_names(data)
                else:
                    return_value = '{}#{}'.format(PUSH_ERROR, UNKNOWN_COMMAND)
            # Several of the helper methods will raise ValueError on wrong
            # input
            except ValueError as exception:
                return_value = '{}#{}'.format(PUSH_ERROR, str(exception))

        PUSHUHLOG.debug('Send back: %s', return_value)
        sock.sendto(return_value.encode('ascii'), self.client_address)

    def _raw_with_names(self, data):
        """Adds raw data to the queue"""
        PUSHUHLOG.debug('Parse raw with names: %s', data)
        data_out = {}
        # Split in data parts e.g: 'codenam1:type:dat1,dat2'. NOTE if no data
        # is passed (data is ''), the split will return '', which will make
        # .split(':') fail
        for part in data.split(';'):
            # Split the part up
            try:
                codename, data_type, data_string = part.split(':')
            except ValueError:
                message = 'The data part \'{}\' did not match the expected '\
                    'format of 3 parts divided by \':\''.format(part)
                PUSHUHLOG.error(message)
                raise ValueError(message)
            # Parse the type
            try:
                type_function = TYPE_FROM_STRING[data_type]
            except KeyError:
                message = 'The data type \'{}\' is unknown. Only {} are '\
                    'allowed'.format(data_type, TYPE_FROM_STRING.keys())
                PUSHUHLOG.error(message)
                raise ValueError(message)
            # Convert the data
            try:
                data_converted = list(
                    [type_function(dat) for dat in data_string.split(',')]
                )
            except ValueError as exception:
                message = 'Unable to convert values to \'{}\'. Error is: {}'\
                    .format(data_type, str(exception))
                PUSHUHLOG.error(message)
                raise ValueError(message)
            # Remove list for length 1 data
            if len(data_converted) == 1:
                data_converted = data_converted[0]
            # Inset the data
            data_out[codename] = data_converted

        # Set data and return ACK message
        return self._set_data(data_out)

    def _json_with_names(self, data):
        """Adds json encoded data to the data queue"""
        PUSHUHLOG.debug('Parse json with names: %s', data)
        try:
            data_dict = json.loads(data)
        except ValueError:
            message = 'The string \'{}\' could not be decoded as JSON'.\
                format(data)
            PUSHUHLOG.error(message)
            raise ValueError(message)
        # Check type (normally not done, but we want to be sure)
        if not isinstance(data_dict, dict):
            message = 'The object \'{}\' returned after decoding the JSON '\
                'string is not a dict'.format(data_dict)
            PUSHUHLOG.error(message)
            raise ValueError(message)

        # Set data and return ACK message
        return self._set_data(data_dict)

    def _set_data(self, data):
        """Sets the data in 'last' and 'updated' and enqueue and/or make
        callback call if the action requires it

        Args:
            data (dict): The data set to set/enqueue/callback

        Returns:
            (str): The request return value
        """
        PUSHUHLOG.debug('Set data: %s', data)
        timestamp = time.time()
        DATA[self.port]['last'] = data
        DATA[self.port]['last_time'] = timestamp
        DATA[self.port]['updated'].update(data)
        DATA[self.port]['updated_time'] = timestamp

        # Put the data in queue for actions that require that
        if DATA[self.port]['action'] in ['enqueue', 'callback_async']:
            DATA[self.port]['queue'].put(data)

        # Execute the callback for actions that require that. Notice, the
        # different branches determines which output format gets send back
        # ACKnowledge or RETurn (value on callback)
        if DATA[self.port]['action'] == 'callback_direct':
            try:
                # Call the callback
                return_value = DATA[self.port]['callback'](data)
                # Format the return value depending on return_format
                if DATA[self.port]['return_format'] == 'json':
                    out = self._format_return_json(return_value)
                elif DATA[self.port]['return_format'] == 'raw':
                    out = self._format_return_raw(return_value)
                elif DATA[self.port]['return_format'] == 'string':
                    out = self._format_return_string(return_value)
                else:
                    # The return format values should be checked on
                    # instantiation
                    message = 'Bad return format. REPORT AS BUG.'
                    out = '{}#{}'.format(PUSH_ERROR, message)
            # pylint: disable=broad-except
            except Exception as exception:  # Catch anything it might raise
                out = '{}#{}'.format(PUSH_EXCEP, str(exception))
        else:
            # Return the ACK message with the interpreted data
            out = '{}#{}'.format(PUSH_ACK, data)

        return out

    @staticmethod
    def _format_return_json(value):
        """Formats the return value as json

        Args:
            value (json serializable): The data structure to serialize with
                JSON

        Returns:
            (str): The request return value
        """
        PUSHUHLOG.debug('Format return json: %s', value)
        try:
            out = '{}#{}'.format(PUSH_RET, json.dumps(value))
        except TypeError as exception:
            out = '{}#{}'.format(PUSH_EXCEP, str(exception))
        return out

    @staticmethod
    def _format_return_string(value):
        """Formats the return value as a string

        Args:
            value (str): Anything with a str representation. The expected type
                IS a str, in which what will be returned is the str itself

        Returns:
            (str): The request return value
        """
        PUSHUHLOG.debug('Format return string: %s', value)
        try:
            out = '{}#{}'.format(PUSH_RET, str(value))
        except Exception as exception:  # pylint: disable=broad-except
            # Have no idea, maybe attribute error
            out = '{}#{}'.format(PUSH_EXCEP, str(exception))
        return out

    def _format_return_raw(self, argument):
        """Formats the value argument in raw format. When used as a return
        value the raw format accepts two argument structures.

        ``argument`` can either be a dict, where the keys are strs and the
        values are simple types or lists with elements of the same simple type.
        This will turn:
            {'answer': 42, 'values': [42, 47], 'answer_good': False}
        into:
            'answer:int:42;values:int:42,47:answer_good:bool:False'

        The other possibility is that ``argument`` is a list of lists. This
        structure is suitable e.g. for passing a list of points. In this case
        all values in the structure must be of the same simple type. This will
        turn:
            [[7.0, 42.0], [7.5, 45.5], [8.0, 47.0]]
        into:
            '7.0,42.0&7.5,45.5&8.0,47.0'

        See the :meth:`.handle` method for details.

        Ars:
            argument (dict or list): The values to to convert

        Returns:
            str: The request return value
        """
        PUSHUHLOG.debug('Format return raw: %s', argument)
        try:
            if argument is None:
                out = '{}#{}'.format(PUSH_RET, 'None')
            elif isinstance(argument, dict):
                out = self._format_return_raw_dict(argument)
            elif isinstance(argument, list):
                out = self._format_return_raw_list(argument)
            else:
                message = 'Return value must be a dict or list with return '\
                    'format \'raw\''
                raise ValueError(message)
        # pylint: disable=broad-except
        except Exception as exception:
            message = 'Raw conversion failed with message'
            out = '{}#{}:{}'.format(PUSH_EXCEP, message, str(exception))

        return out

    @staticmethod
    def _format_return_raw_dict(argument):
        """Formats return raw value which is a dict. See :meth:`._format_return_raw` for
        details

        Args:
            argument (dict): The dict to be serialized manually

        Returns:
            str: The dict raw serialization string
        """
        PUSHUHLOG.debug('Format return raw dict: %s', argument)
        # Items holds the strings for each key, value pair e.g.
        # 'codename1:type:data'
        items = []
        # Manually serializing is ugly ...! and probably error prone :( Where
        # possible use JSON, where people smarter than me have though about
        # corner cases
        for key, value in argument.items():
            if isinstance(value, list) and len(value) > 0:
                # Check all values in list are of same type
                types = [type(element) for element in value]
                element_type = types[0]
                element_type_name = six.text_type(element_type.__name__)
                if types != len(types) * [element_type]:
                    message = 'With return format raw, value in list must have same type'
                    raise ValueError(message)

                value_string = ','.join([str(element) for element in value])
            elif isinstance(value, list) and len(value) == 0:
                # An empty list gets turned into type='', value=''
                element_type_name = ''
                value_string = ''
            else:
                # Single element conversion
                element_type_name = six.text_type(type(value).__name__)
                value_string = '{}'.format(str(value))

            # We always call it str
            if sys.version_info[0] == 2 and element_type_name == 'unicode':
                element_type_name = 'str'

            # Check that the element type makes sense for raw conversion
            if element_type_name not in ['int', 'float', 'bool', 'str']:
                message = 'With return format raw, the item type can '\
                    'only be one of \'int\', \'float\', \'bool\' and '\
                    '\'str\'. Object: \'{}\' is of type: {}'.format(
                        value, element_type_name)
                raise TypeError(message)

            # pylint: disable=maybe-no-member
            item_str = '{}:{}:{}'.format(str(key), element_type_name, value_string)
            items.append(item_str)

        return '{}#{}'.format(PUSH_RET, ';'.join(items))

    @staticmethod
    def _format_return_raw_list(argument):
        """Formats return raw value which is a list of lists. See
        :meth:`._format_return_raw` for details

        Args:
            argument (list): The list of lists to be raw serialized

        Returns
            str: The raw serialized string
        """
        PUSHUHLOG.debug('Format return raw list: %s', argument)
        types = []
        # List of strings with points as x,y
        items = []
        for item in argument:
            if not isinstance(item, list):
                message = 'With return format raw on a list, the elements '\
                    'themselves be lists'
                raise ValueError(message)
            types += [type(element) for element in item]
            converted = [str(element) for element in item]
            items.append(','.join(converted))

        # Check that they are all of same type
        element_type = types[0]
        if types != len(types) * [element_type]:
            message = 'With return format raw on a list of lists, all values '\
                ' in list must have same type. Types are: {}'.format(types)
            raise ValueError(message)

        # Check that the element type makes sense for raw conversion
        if element_type not in [int, float, bool, str]:
            message = 'With return format raw, the item type can only be one '\
                'of \'int\', \'float\', \'bool\' and \'str\'. The type is: {}'\
                    .format(element_type)
            raise TypeError(message)

        return '{}#{}:{}'.format(PUSH_RET, element_type.__name__,
                                 '&'.join(items))


DPUSHSLOG = logging.getLogger(__name__ + '.DataPushSocket')
DPUSHSLOG.addHandler(logging.NullHandler())
class DataPushSocket(threading.Thread):
    """This class implements a data push socket and provides options for
    enqueuing, calling back or doing nothing on reciept of data
    """

    # pylint: disable=too-many-branches
    def __init__(self, name, port=8500, action='store_last', queue=None,
                 callback=None, return_format='json', check_activity=False,
                 activity_timeout=900):
        """Initializes the DataPushSocket

        Arguments:
            name (str): The name of the socket server. Used for identification
                and therefore should contain enough information about location
                and purpose to unambiguously identify the socket server. E.g:
                ``'Driver push socket for giant laser on the moon'``
            port (int): The network port to start the socket server on (default
                is 8500)
            action (string): Determined the action performed on incoming data.
                The possible values are:

                 * ``'store_last'`` (default and always) the incoming data
                   will be stored, as a dict, only in the two properties;
                   :attr:`~.last` and :attr:`~.updated`, where :attr:`~.last`
                   contains only the data from the last reception and
                   :attr:`~.updated` contains the newest value for each
                   codename that has been received ever. Saving to these two
                   properties **will always be done**, also with the other
                   actions.
                 * ``'enqueue'``; the incoming data will also be enqueued
                 * ``'callback_async'`` a callback function will also be
                   called with the incoming data as an argument. The calls to
                   the callback function will in this case happen
                   asynchronously in a seperate thread
                 * ``'callback_direct'`` a callback function will also be
                   called and the result will be returned, provided it has a
                   str representation. The return value format can be set with
                   ``return_format``
            queue (Queue.Queue): If action is 'enqueue' and this value is set,
                it will be used as the data queue instead the default which is
                a new :py:class:`Queue.Queue` instance without any further
                configuration.
            callback (callable): A callable that will be called on incoming
                data. The callable should accept a single argument that is the
                data as a dictionary.
            return_format (str): The return format used when sending callback
                return values back (used with the ``'callback_direct'``
                action). The value can be:

                 * ``'json'``, which, if possible, will send the value back
                   encoded as json
                 * ``'raw'`` which, if possible, will encode a dict of values,
                   a list of lists or None. If it is a dict, each value may
                   be a list of values with same type, in the same way as they
                   are received with the ``'raw_wn'`` command in the
                   :meth:`.PushUDPHandler.handle` method. If the return value
                   is a list of lists (useful e.g. for several data points),
                   then **all** values must be of the same type. The format
                   sent back looks like: ``'1.0,42.0&1.5,45.6&2.0,47.0'``,
                   where '&' separates the inner lists and ',' the points in
                   those lists
                 * ``'string'`` in which the string representation of the value the
                   call back returns will be sent back. NOTE: These string
                   representations may differ between Python 2 and 3, so do not parse
                   them

        """
        DPUSHSLOG.info('Initialize with: %s', call_spec_string())
        # Init thread
        super(DataPushSocket, self).__init__()
        self.daemon = True
        self._stop = False

        # Init local data and action
        self.port = port
        self.action = action

        # Raise exception on invalid argument combinations
        if queue is not None and action != 'enqueue':
            message = 'The \'queue\' argument can only be used when the '\
                'action is \'enqueue\''
            raise ValueError(message)
        if callback is not None and action not in\
                ['callback_async', 'callback_direct']:
            message = 'The \'callback\' argument can only be used when the '\
                'action is \'callback_async\' or \'callback_direct\''
            raise ValueError(message)
        if action in ['callback_async', 'callback_direct']:
            if not callable(callback):
                message = 'Value for callback: \'{}\' is not callable'\
                    .format(callback)
                raise ValueError(message)
        if return_format not in ['json', 'raw', 'string']:
            message = 'The \'return_format\' argument may only be one of the '\
                '\'json\', \'raw\' or \'string\' values'
            raise ValueError(message)

        # Set callback and queue depending on action
        self._callback_thread = None
        content = {
            'action': action, 'last': None, 'type': 'push', 'updated': {},
            'last_time': None, 'updated_time': None, 'name': name,
            'activity': {
                'check_activity': check_activity,
                'activity_timeout': activity_timeout,
                'last_activity': time.time(),
            }
        }
        if action == 'store_last':
            pass
        elif action == 'enqueue':
            if queue is None:
                content['queue'] = Queue.Queue()
            else:
                content['queue'] = queue
        elif action == 'callback_async':
            content['queue'] = Queue.Queue()
            self._callback_thread = CallBackThread(content['queue'], callback)
        elif action == 'callback_direct':
            content['callback'] = callback
            content['return_format'] = return_format
        else:
            message = 'Unknown action \'{}\'. Must be one of: [\'store_last\', \'enqueue\', '\
                      '\'callback_async\', \'callback_direct\']'.format(action)
            raise ValueError(message)

        # Setup server
        try:
            self.server = SocketServer.UDPServer(('', port), PushUDPHandler)
        except socket.error as error:
            if error.errno == 98:
                # See custom exception message to understand this
                raise PortStillReserved()
            else:
                raise error

        # Only put this socket in the DATA variable, if we succeed in
        # initializing it
        DATA[port] = content
        DPUSHSLOG.debug('DPS: Initialized')

    def run(self):
        """Starts the UPD socket server"""
        DPUSHSLOG.info('DPS: Start')
        if self._callback_thread is not None:
            self._callback_thread.start()
        self.server.serve_forever()
        DPUSHSLOG.info('DPS: Run ended')

    def stop(self):
        """Stops the UDP socket server

        .. note:: Closing the server **and** deleting the
            :py:class:`SocketServer.UDPServer` socket instance is necessary to
            free up the port for other usage
        """
        DPUSHSLOG.debug('DPS: Stop requested')
        if self._callback_thread is not None:
            self._callback_thread.stop()
        time.sleep(0.1)
        self.server.shutdown()
        # Wait 0.1 sec to prevent the interpreter from destroying the
        # environment before we are done
        time.sleep(0.1)
        # Delete the data, to allow forming another socket on this port
        del DATA[self.port]
        DPUSHSLOG.info('DPS: Stopped')

    @property
    def queue(self):
        """Gets the queue, returns None if ``action`` is ``'store_last'`` or
        ``'callback_direct'``
        """
        DPUSHSLOG.debug('DPS: queue property used')
        return DATA[self.port].get('queue')

    @property
    def last(self):
        """Gets a copy of the last data

        Returns
            tuple: ``(last_data_time, last_data)`` where ``last_data`` is the
                data from the last reception and ``last_data_time`` is the Unix
                timestamp of that reception. Returns ``(None, None)`` if no
                data has been recieved.
        """
        DPUSHSLOG.debug('DPS: last property used')
        if DATA[self.port]['last'] is None:
            last = DATA[self.port]['last']
        else:
            last = DATA[self.port]['last'].copy()
        return DATA[self.port]['last_time'], last

    @property
    def updated(self):
        """Gets a copy of the updated total data, returns empty dict if no data
        has been received yet

        Returns:
            tuple: ``(updated_data_time, updated_data)`` where ``updated_data``
                is the total updated data after the last reception and
                ``updated_data_time`` is the Unix timestamp of that reception.
                Returns ``(None, {})`` if no data has been recieved.
        """
        DPUSHSLOG.debug('DPS: updated property used')
        return (DATA[self.port]['updated_time'],
                DATA[self.port]['updated'].copy())

    def set_last_to_none(self):
        """Sets the last data point and last data point time to None"""
        DPUSHSLOG.debug('DPS: Set last to none')
        DATA[self.port]['last'] = None
        DATA[self.port]['last_time'] = None

    def clear_updated(self):
        """Clears the total updated data and set the time of last update to
        None
        """
        DPUSHSLOG.debug('DPS: Clear updated')
        DATA[self.port]['updated'].clear()
        DATA[self.port]['updated_time'] = None

    def poke(self):
        """Pokes the socket server to let it know that there is activity"""
        if DATA[self.port]['activity']['check_activity']:
            DATA[self.port]['activity']['last_activity'] = time.time()


CBTLOG = logging.getLogger(__name__ + '.CallBackThread')
CBTLOG.addHandler(logging.NullHandler())
class CallBackThread(threading.Thread):
    """Class to handle the calling back for a DataReceiveSocket"""

    def __init__(self, queue, callback):
        """Initialize the local variables

        Args:
            queue (Queue.Queue): The queue that queues up the arguments for the
                callback function
            callback (callable): The callable that will be called when there
                are items in the queue
        """
        CBTLOG.info('Initialize with: %s', call_spec_string())
        # Initialize the thread
        super(CallBackThread, self).__init__()
        self.daemon = True
        self._stop = False

        # Set variables
        self.queue = queue
        self.callback = callback
        CBTLOG.debug('CBT: Initialized')

    def run(self):
        """Starts the calling back"""
        CBTLOG.info('CBT: Run')
        while not self._stop:
            # get a item from the queue and call back
            try:
                # The get times out every second, to make sure that the thread
                # can be shut down
                item = self.queue.get(True, 1)
                self.callback(item)
                CBTLOG.debug('CBT: Callback called with arg: %s', item)
            except Queue.Empty:
                pass
        CBTLOG.info('CBT: Run stopped')

    def stop(self):
        """Stops the calling back"""
        CBTLOG.debug('CBT: Stop requested')
        self._stop = True
        CBTLOG.info('CBT: Stopped')


class PortStillReserved(Exception):
    """Custom exception to explain socket server port still reserved even after
    closing the port
    """
    def __init__(self):
        message = 'Even when a socket server has been requested '\
            'closed, the socket module will still keep it reserved for some '\
            'time (maybe up to a minute), to allow for clearing up lower '\
            'level networking components. If it is required to open and '\
            'close socket servers fast on the same ports, this behavior can '\
            'be changed by invoking:'\
            '\n    import SocketServer'\
            '\n    SocketServer.UDPServer.allow_reuse_address = True'\
            '\nbefore instantiation.'
        super(PortStillReserved, self).__init__(message)


LSLOG = logging.getLogger(__name__ + '.LiveSocket')
LSLOG.addHandler(logging.NullHandler())
class LiveSocket(object):
    """This class implements a Live Socket

    As of version 2 LiveSocket there are a few new features to note:

     1. There is now support for values of any json-able object. The values can of course
        only be shown in a graph if they are numbers, but all other types can be shown in
        a table.
     2. There is now support for generic xy data. Simply use :meth:`.set_point` or
        :meth:`set_batch` and give it x, y values.

    """

    def __init__(self, name, codenames, live_server=None, no_internal_data_pull_socket=False,
                 internal_data_pull_socket_port=8000):
        """Intialize the LiveSocket

        Args:
            name (str): The name of the socket
            codenames (sequence): The codenames for the different data channels on this
                LiveSocket
            live_server (sequence): 2 element sequence of hostname and port for the live
                server to connect to. Defaults to `(Settings.common_liveserver_host,
                Settings.common_liveserver_host)`.
            no_internal_data_pull_socket (bool): Whether to not open an internal
                DataPullSocket. Defaults to False. See note below.
            internal_data_pull_socket_port (int): Port for the internal DataPullSocket.
                Defaults to 8000. See note below.

        .. note:: In general, any socket should also work as a status socket. But since
            the new design of the live socket, it no longers runs a UDP server, as would
            be required for it to work as a status socket. Therefore, LiveSocket now
            internally runs a DataPullSocket on port 8000 (that was the old LiveSocket
            port) to work as a status socket. With default setting, everything should work
            as before.

        """
        LSLOG.info('Init')
        self.codename_set = set(codenames)
        if live_server is None:
            live_server = (SETTINGS.common_liveserver_host, SETTINGS.common_liveserver_port)
        liveserver_hostname, self.liveserver_port = live_server
        # Translate live server hostname to IP-address to avoid DNS lookup on every
        # transmission
        self.liveserver_ip = socket.gethostbyname(liveserver_hostname)

        # Open up UDP socket and get hostname og this machine
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.hostname = socket.gethostname()

        # A live socket exposes a DataPullSocket, since we expect to always have access to
        # the system information, and because, since we have all the information there
        # anyway, there is not reason not to make it available in a socket
        if no_internal_data_pull_socket:
            self._internal_pull_socket = None
        else:
            self._internal_pull_socket = DataPullSocket(
                name, codenames, port=internal_data_pull_socket_port
            )

    def start(self):
        """Starts the internal DataPullSocket"""
        if self._internal_pull_socket:
            self._internal_pull_socket.start()

    def stop(self):
        """Stop the internal DataPullSocket"""
        if self._internal_pull_socket:
            self._internal_pull_socket.stop()

    def set_batch(self, data):
        """Set a batch of points now

        Args:
            data (dict): Batch of data on the form {codename1: (x1, y1), codename2:
                (x2, y2)}. Note, that for the live socket system, the y values need not
                be data in the form of a float, it can also be an int, bool or str. This
                is done to make it possible to also transmit e.g. equipment status to the
                live pages.

        .. note:: All data is sent to the live socket proxy and onwards to the web browser
            clients as batches, so if the data is on batch form, might as well send it as
            such and reduce the number of transmissions.

        """
        # Set the values on the DataPullSocket
        for key, value in data.items():
            if key not in self.codename_set:
                message = 'The codename: \'{}\' is not registered'.format(key)
                LSLOG.error(message)
                raise RuntimeError(message)
            if self._internal_pull_socket:
                self._internal_pull_socket.set_point(key, value)

        # Send the data to the live socket proxy
        dump = json.dumps({'host': self.hostname, 'data': data})
        self.socket.sendto(dump.encode('utf-8'), (self.liveserver_ip, self.liveserver_port))

    def set_batch_now(self, data):
        """Set a batch of point now

        Args:
            data (dict): A mapping of codenames to values without times or x-values (see
                example below)

        The format for data is::

            {'measurement1': 47.0, 'measurement2': 42.0}

        """
        now = time.time()
        self.set_batch({key: (now, value) for key, value in data.items()})

    def set_point_now(self, codename, value):
        """Sets the current value for codename using the current time as x

        Args:
            codename (str): Name for the measurement whose current value should
                be set
            value (float, int, bool or str): value
        """
        self.set_batch({codename: (time.time(), value)})
        LSLOG.debug('Added time to value and called set_point')

    def set_point(self, codename, point):
        """Sets the current point for codename

        Args:
            codename (str): Name for the measurement whose current point should
                be set
            point (list or tuple): Current value "point" as a list (or tuple) of items,
                the first must be a float, the second can be float, int, bool or str
        """
        self.set_batch({codename: point})
        LSLOG.debug('Point %s for \'%s\' set', tuple(point), codename)

    def reset(self, codenames):
        """Send the reset signal for codenames

        Args:
            codenames (list): List of codenames
        """
        self.set_batch({codename: 'RESET' for codename in codenames})


### Module variables
#: The list of characters that are not allowed in code names
BAD_CHARS = ['#', ',', ';', ':', '&']
#: The string returned if an unknown command is sent to the socket
UNKNOWN_COMMAND = 'UNKNOWN_COMMMAND'
#: The string used to indicate old or obsoleted data
OLD_DATA = 'OLD_DATA'
#: The answer prefix used when a push failed
PUSH_ERROR = 'ERROR'
#: The answer prefix used when a push succeds
PUSH_ACK = 'ACK'
#: The answer prefix for when a callback or callback value formatting produces
#: an exception
PUSH_EXCEP = 'EXCEP'
#: The answer prefix for a callback return value
PUSH_RET = 'RET'
#:The variable used to contain all the data.
#:
#:The format of the DATA variable is the following. The DATA variable is a
#:dict, where each key is an integer port number and the value is the data for
#:the socket server on that port. The data for each individual socket server is
#:always a dict, but the contained values will depend on which kind of socket
#:server it is, Examples below.
#:
#:For a :class:`DateDataPullSocket` the dict will resemble this example:
#:
#: .. code-block:: python
#:
#:  {'activity': {'activity_timeout': 900,
#:                'check_activity': True,
#:                'last_activity': 1413983209.82526},
#:   'codenames': ['var1'],
#:   'data': {'var1': (0.0, 0.0)},
#:   'name': 'my_socket',
#:   'timeouts': {'var1': None},
#:   'type': 'date'}
#:
#:For a :class:`DataPullSocket` the dict will resemble this example:
#:
#: .. code-block:: python
#:
#:  {'activity': {'activity_timeout': 900,
#:                'check_activity': True,
#:                'last_activity': 1413983209.825451},
#:   'codenames': ['var1'],
#:   'data': {'var1': (0.0, 0.0)},
#:   'name': 'my_data_socket',
#:   'timeouts': {'var1': None},
#:   'timestamps': {'var1': 0.0},
#:   'type': 'data'}
#:
#:For a :class:`DataPushSocket` the dict will resemble this example:
#:
#: .. code-block:: python
#:
#:  {'action': 'store_last',
#:   'activity': {'activity_timeout': 900,
#:                'check_activity': False,
#:                'last_activity': 1413983209.825681},
#:   'last': None,
#:   'last_time': None,
#:   'name': 'my_push_socket',
#:   'type': 'push',
#:   'updated': {},
#:   'updated_time': None}
#:
DATA = {}
#: The dict that transforms strings to convertion functions
TYPE_FROM_STRING = {'int': int, 'float': float, 'str': str,
                    'bool': bool_translate}


def run_module():
    """This functions sets"""
    import math

    def push_callback(incoming):
        """Calback function for the push socket"""
        print('Push socket got:', incoming)

    push_socket = DataPushSocket(
        'module_test_push_socket', action='callback_direct', callback=push_callback
    )
    push_socket.start()
    print('Started DataPushSocket on port 8500 with name "module_test_push_socket"')

    live_socket = LiveSocket(
        'dummy_live_socket',
        codenames=('dummy_sine_one', 'dummy_sine_two'),
        no_internal_data_pull_socket=True,
    )
    live_socket.start()
    print('Started live_socket. Using hostname {}'.format(live_socket.hostname))

    try:
        while True:
            print('Send new points live socket')
            live_socket.set_point_now('dummy_sine_one', math.sin(time.time()))
            live_socket.set_point_now('dummy_sine_two', math.sin(time.time() + math.pi))
            time.sleep(1)
    except KeyboardInterrupt:
        push_socket.stop()
        print('Stopped DataPushSocket on port 8500 with name "module_test_push_socket"')
        live_socket.stop()
        print('Stopped LiveSocket')
        time.sleep(2)


if __name__ == '__main__':
    run_module()
