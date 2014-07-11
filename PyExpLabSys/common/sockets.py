# -*- coding: utf-8 -*-
"""The sockets module contains various implementations of UDP socket servers
(at present 4 in total) for transmission of data over the network. The
different implementations tailored for a specific purposes, as described below.

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
   different data channel by codenames and has time out functionality to
   prevent servcing old data.
 * **DataPushSocket** (:class:`.DataPushSocket`) This socket is used to recieve
   data from the network. The
   data is received in dictionary form and it identifies the data channels by
   codenames (keys) in the dictionaries. It will save the last point, and the
   last value for each codename. It also has the option to, for each received
   data set, to put them in a queue (that the user can then empty) or to call
   a callback function with the received data as en argument.
 * **LiveSocket** (:class:`.LiveSocket`) This socket is a special pull socket
   used only for serving
   data to the a live socket server. The idea is that these can be used to live
   stream data to web-pages. (UNDER DEVELOPMENT, DON'T USE).

.. warning :: The LiveSocket is still under development, which means that its
 interface is likely to change. Do not include it in critical code just yet.

.. note:: The module variable :data:`.DATA` is a dict shared for all socket
 servers started from this module. It contains all the data, queues, settings
 etc. It can be a good place to look if, to get a behind the scenes look at what
 is happening.
"""

import threading
import socket
import SocketServer
import time
import json
import Queue
import logging
LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
LOGGER.addHandler(logging.NullHandler())
from .utilities import call_spec_string


def bool_translate(string):
    """Return boolean value from strings 'True' or 'False'"""
    if not str(string) in ['True', 'False']:
        message = 'Cannot translate the string \'{}\' to a boolean. Only the '\
            'strings \'True\' or \'False\' are allowed'
        raise ValueError(message)        
    return True if str(string) == 'True' else False


PULLUHLOG = logging.getLogger(__name__ + '.PullUDPHandler')
PULLUHLOG.addHandler(logging.NullHandler())
class PullUDPHandler(SocketServer.BaseRequestHandler):
    """Request handler for the :class:`.DateDataPullSocket` and
    :class:`.DateDataPullSocket` socket servers. The commands this request
    handler understands are documented in the :meth:`.handle` method.
    """

    def handle(self):
        """Return data corresponding to the request
        
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
        """
        command = self.request[0]
        self.port = self.server.server_address[1]
        socket = self.request[1]
        PULLUHLOG.debug('Request \'{}\' received from {} on port {}'\
            .format(command, self.client_address, self.port))

        if command.count('#') == 1:
            data = self._single_value(command)
        else:
            # The name command if also handled here
            data = self._all_values(command)

        socket.sendto(data, self.client_address)
        PULLUHLOG.debug('Sent back \'{}\' to {}'\
            .format(data, self.client_address))

    def _single_value(self, command):
        """Return a string for a single point

        Args:
            command (str): Complete command

        Returns:
            str: The data as a string (or an error) to be sent back
        """
        PULLUHLOG.debug('Parsing single value command: {}'.format(command))
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

        Args:
            command (str): Complete command

        Returns:
            str: The data as a string (or an error) to be sent back
        """
        PULLUHLOG.debug('Parsing all-values command: {}'.format(command))
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
        # Return the socket server name
        elif command == 'name':
            out = DATA[self.port]['name']
        # The command is not known
        else:
            out = UNKNOWN_COMMAND

        return out

    def _old_data(self, codename):
        """Check if the data for codename has timed out

        Args:
            codename (str): The codename whose data should be checked for
                timeout

        Returns:
            bool: Whether the data is too old or not
        """
        PULLUHLOG.debug('Check if data for \'{}\' is too old'.format(codename))
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

    def __init__(self, name, codenames, port, default_x, default_y, timeouts,
                 init_timeouts=True, handler_class=PullUDPHandler):
        """For parameter description of ``name``, ``codenames``, ``port``,
        ``default_x``, ``default_y`` and ``timeouts`` see
        :meth:`.DataPullSocket.__init__` or
        :meth:`.DateDataPullSocket.__init__`.

        Args:
            init_timeouts (bool): Whether timeouts should be instantiated in
                the :data:`.DATA` module variable
            handler_class (Sub-class of SocketServer.BaseRequestHandler): The
                UDP handler to use in the server
        """
        CDPULLSLOG.info('Initialize with: {}'.format(call_spec_string()))
        # Init thread
        super(CommonDataPullSocket, self).__init__()
        self.daemon = True
        # Init local data
        self.port = port

        # Check for existing servers on this port
        global DATA
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
        # Check for name that has 

        # Prepare DATA
        DATA[port] = {'codenames': list(codenames), 'data': {}, 'name': name}
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
                CDPULLSLOG.error('Port \'{}\' still reserved'.format(port))
                raise PortStillReserved()
            else:
                raise error
        CDPULLSLOG.debug('Initialized')

    def run(self):
        """Start the UPD socket server"""
        CDPULLSLOG.info('Run')
        self.server.serve_forever()
        CDPULLSLOG.info('Run ended')

    def stop(self):
        """Stop the UDP server

        .. note:: Closing the server **and** deleting the socket server
                instance is necessary to free up the port for other usage
        """
        CDPULLSLOG.debug('Stop requested')
        self.server.shutdown()
        # Wait 0.1 sec to prevent the interpreter from destroying the
        # environment before we are done if this is the last thread
        time.sleep(0.1)
        # Delete the data, to allow forming another socket on this port
        del DATA[self.port]
        CDPULLSLOG.info('Stopped')


DPULLSLOG = logging.getLogger(__name__ + '.DataPullSocket')
DPULLSLOG.addHandler(logging.NullHandler())
class DataPullSocket(CommonDataPullSocket):
    """This class implements a UDP socket server for serving x, y type data.
    The UDP server uses the :class:`.PullUDPHandler` class to handle
    the UDP requests. The commands that can be used with this socket server are
    documented in the :meth:`.PullUDPHandler.handle()` method.
    """

    def __init__(self, name, codenames, port=9010, default_x=47, default_y=47,
                 timeouts=None):
        """Init data and UPD server

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
        """
        DPULLSLOG.info('Initialize with: {}'.format(call_spec_string()))
        # Run super init to initialize thread, check input and initialize data
        super(DataPullSocket, self).__init__(
            name, codenames, port=port, default_x=default_x, default_y=default_y,
            timeouts=timeouts
        )
        DATA[port]['type'] = 'data'
        # Init timestamps
        DATA[port]['timestamps'] = {}
        for name in codenames:
            DATA[port]['timestamps'][name] = 0.0
        DPULLSLOG.debug('Initialized')

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
        DPULLSLOG.debug('Point {} for \'{}\' set'.format(tuple(point), codename))


DDPULLSLOG = logging.getLogger(__name__ + '.DateDataPullSocket')
DDPULLSLOG.addHandler(logging.NullHandler())
class DateDataPullSocket(CommonDataPullSocket):
    """This class implements a UDP socket server for serving data as a function
    of time. The UDP server uses the :class:`.PullUDPHandler` class to handle
    the UDP requests. The commands that can be used with this socket server are
    documented in the :meth:`.PullUDPHandler.handle()` method.

    """

    def __init__(self, name, codenames, port=9000, default_x=0, default_y=47,
                 timeouts=None):
        """Init data and UPD server

        Args:
            name (str): The name of the DateDataPullSocket server. Used for
                identification and therefore should contain enough information
                about location and purpose to unambiguously identify the socket
                server. E.g:
                ``'DateDataPullSocket with data from giant laser on the moon'``
            codenames (list): List of codenames for the measurements. The names
                must be unique and cannot contain the characters: ``#,;:`` and
                SPACE
            port (int): Network port to use for the socket (default 9000)
            default_x (float): The x value the measurements are initiated with
            default_y (float): The y value the measurements are initiated with
            timeouts (float or list of floats): The timeouts (in seconds as
                floats) that determines when the date data socket regards the
                data as being to old and reports that
        """
        DDPULLSLOG.info('Initialize with: {}'.format(call_spec_string()))
        # Run super init to initialize thread, check input and initialize data
        super(DateDataPullSocket, self).__init__(
            name, codenames, port=port, default_x=default_x,
            default_y=default_y, timeouts=timeouts
        )
        # Set the type
        DATA[port]['type'] = 'date'
        DDPULLSLOG.debug('Initialized')

    def set_point_now(self, codename, value):
        """Set the current y-value for codename using the current time as x
        
        :param codename: Name for the measurement whose current value should be
            set
        :type codename: str
        :param value: y-value
        :type value: float
        """
        self.set_point(codename, (time.time(), value))
        DDPULLSLOG.debug('Added time to value and called set_point')

    def set_point(self, codename, point):
        """Set the current point for codename
        
        :param codename: Name for the measurement whose current point should be
            set
        :type codename: str
        :param point: Current point as a list (or tuple) of 2 floats: [x, y]
        :type point: list or tuple
        """
        DATA[self.port]['data'][codename] = tuple(point)
        DDPULLSLOG.debug('Point {} for \'{}\' set'.format(tuple(point), codename))


PUSHUHLOG = logging.getLogger(__name__ + '.PushUDPHandler')
PUSHUHLOG.addHandler(logging.NullHandler())
class PushUDPHandler(SocketServer.BaseRequestHandler):
    """This class handles the UDP requests for the :class:`.DataRecieveSocket`
    """

    def handle(self):
        """Set data corresponding to the request

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

        """
        request = self.request[0]
        PUSHUHLOG.debug('Request \'{}\'received'.format(request))
        self.port = self.server.server_address[1]
        socket = self.request[1]

        if request == 'name':
            return_value = '{}#{}'.format(PUSH_ACK, DATA[self.port]['name'])
        elif request.count('#') != 1:
            return_value = UNKNOWN_COMMAND
        else:
            command, data = request.split('#')
            try:
                if command == 'json_wn':
                    return_value = self._json_with_names(data)
                elif command == 'raw_wn':
                    return_value = self._raw_with_names(data)
                else:
                    return_value = UNKNOWN_COMMAND
            except ValueError as exception:
                return_value = '{}#{}'.format(PUSH_ERROR, exception.message)

        PUSHUHLOG.debug('Send back: {}'.format(return_value))
        socket.sendto(return_value, self.client_address)

    def _raw_with_names(self, data):
        """Add raw data to the queue"""
        PUSHUHLOG.debug('Parse raw with names')
        data_out = {}
        # Split in data parts e.g: 'codenam1:type:dat1,dat2'
        for part in data.split(';'):
            # Split the part up
            try:
                codename, data_type, data_string = part.split(':')
            except ValueError:
                message = 'The data part \'{}\' did not match the expected '\
                    'format of 3 parts divided by \':\''.format(part)
                PUSHUHLOG.error('{}'.format(message))
                raise ValueError(message)
            # Parse the type
            try:
                type_function = TYPE_FROM_STRING[data_type]
            except KeyError:
                message = 'The data type \'{}\' is unknown. Only {} are '\
                    'allowed'.format(data_type, TYPE_FROM_STRING.keys())
                PUSHUHLOG.error('{}'.format(message))
                raise ValueError(message)
            # Convert the data
            try:
                data_converted = list(
                    [type_function(dat) for dat in data_string.split(',')]
                )
            except ValueError as exception:
                message = 'Unable to convert values to \'{}\'. Error is: {}'\
                    .format(data_type, exception.message)
                PUSHUHLOG.error('{}'.format(message))
                raise ValueError(message)
            # Remove list for length 1 data
            if len(data_converted) == 1:
                data_converted = data_converted[0]
            # Inset the data
            data_out[codename] = data_converted

        # Set data and return ACK message
        return self._set_data(data_out)

    def _json_with_names(self, data):
        """Add json encoded data to the data queue"""
        PUSHUHLOG.debug('Parse json')
        try:
            data_dict = json.loads(data)
        except ValueError:
            message = 'The string \'{}\' could not be decoded as JSON'.\
                format(data)
            PUSHUHLOG.error('{}'.format(message))
            raise ValueError(message)
        # Check type (normally not done, but we want to be sure)
        if not isinstance(data_dict, dict):
            message = 'The object \'{}\' returned after decoding the JSON '\
                'string is not a dict'.format(data_dict)
            PUSHUHLOG.error('{}'.format(message))
            raise ValueError(message)

        # Set data and return ACK message
        return self._set_data(data_dict)

    def _set_data(self, data):
        """Set the data in 'last' and 'updated' and enqueue it if the action
        requires it
        """
        PUSHUHLOG.debug('Set data')
        timestamp = time.time()
        DATA[self.port]['last'] = data
        DATA[self.port]['last_time'] = timestamp
        DATA[self.port]['updated'].update(data)
        DATA[self.port]['updated_time'] = timestamp
        # Put the data in queue for actions that require that
        if DATA[self.port]['action'] in ['enqueue', 'callback_async']:
            DATA[self.port]['queue'].put(data)
        # Return the ACK message with the interpreted data
        return '{}#{}'.format(PUSH_ACK, data)


DPUSHSLOG = logging.getLogger(__name__ + '.DataPushSocket')
DPUSHSLOG.addHandler(logging.NullHandler())
class DataPushSocket(threading.Thread):
    """This class implements a data push socket and provides options for
    enqueuing, calling back or doing nothing on reciept of data
    """

    def __init__(self, name, port=8500, action='store_last', queue=None,
                 callback=None):
        """Initialiaze the DataReceiveSocket
        
        Arguments:
            name (str): The name of the socket server. Used for identification
                and therefore should contain enough information about location
                and purpose to unambiguously identify the socket server. E.g:
                ``'Driver push socket for giant laser on the moon'``
            port (int): The network port to start the socket server on (default
                is 8500)
            action (string): Determined the action performed on incoming data.
                If set to ``'store_last'`` (default) the incoming data will be
                stored, as a dict, only in the two properties;
                :attr:`~.last` and :attr:`~.updated`, where :attr:`~.last`
                contains only the data from the last reception and
                :attr:`~.updated` contains the newest value for each codename
                that has been received ever. Saving to these two properties
                will always be done, also with the other actions. If ``action``
                is set to ``'enqueue'`` the incoming data will also be
                enqueued. If set to ``'callback_async'``, a callback function
                will also be called with the incoming data as an argument. The
                calls to the callback function will in this case happen
                asynchronously in a seperate thread. If ``action`` is set to
                ``'callback_direct'`` a callback function will also be called
                and the result will be returned, provided it has a str
                representation.
            queue (Queue): If action is 'enqueue' and this value is set, it
                will be used as the data queue instead the default which is a
                new Queue.Queue() instance without any further configuration.
            callback (callable): A callable that will be called on incoming
                data. The callable should accept a single argument that is the
                data as a dictionary.
        """
        DPUSHSLOG.info('Initialize with: {}'.format(call_spec_string()))
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

        # Set callback and queue depending on action
        self._callback_thread = None
        content = {'action': action, 'last': None, 'updated': {},
                   'last_time': None, 'updated_time': None, 'name': name}
        if action == 'store_last':
            pass
        elif action == 'enqueue':
            if queue is None:
                content['queue'] = Queue.Queue()
            else:
                content['queue'] = queue
        elif action == 'callback_async':
            if not callable(callback):
                message = 'Value for callback: \'{}\' is not callable'\
                    .format(callback)
                raise ValueError(message)
            content['queue'] = Queue.Queue()
            self._callback_thread = CallBackThread(content['queue'], callback)
        else:
            message = 'Unknown action \'{}\'. Must be one of: {}'.\
                format(action, ['store_last', 'enqueue', 'callback_async',
                                'callback_direct'])
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
        """Start the UPD socket server"""
        DPUSHSLOG.info('DPS: Start')
        if self._callback_thread is not None:
            self._callback_thread.start()
        self.server.serve_forever()
        DPUSHSLOG.info('DPS: Run ended')

    def stop(self):
        """Stop the UDP socket server

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
        """Get the queue, returns None if ``action`` is ``'store_last'``"""
        DPUSHSLOG.info('DPS: queue property used')
        return DATA[self.port].get('queue')

    @property
    def last(self):
        """Get a copy of the last data
        
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
        """Get a copy of the updated total data, returns empty dict if no data
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
        """Set the last data point and last data point time to None"""
        DPUSHSLOG.debug('DPS: Set last to none')
        DATA[self.port]['last'] = None
        DATA[self.port]['last_time'] = None

    def clear_updated(self):
        """Clear the total updated data and set the time of last update to
        None
        """
        DPUSHSLOG.debug('DPS: Clear updated')
        DATA[self.port]['updated'].clear()
        DATA[self.port]['updated_time'] = None


CBTLOG = logging.getLogger(__name__ + '.CallBackThread')
CBTLOG.addHandler(logging.NullHandler())
class CallBackThread(threading.Thread):
    """Class to handle the calling back for a DataReceiveSocket"""

    def __init__(self, queue, callback):
        """Initialize the local variables"""
        CBTLOG.info('Initialize with: {}'.format(call_spec_string()))
        # Initialize the thread
        super(CallBackThread, self).__init__()
        self.daemon = True
        self._stop = False

        # Set variables
        self.queue = queue
        self.callback = callback
        CBTLOG.debug('CBT: Initialized')

    def run(self):
        """Start the calling back"""
        CBTLOG.info('CBT: Run')
        while not self._stop:
            # get a item from the queue and call back
            try:
                # The get times out every second, to make sure that the thread
                # can be shut down
                item = self.queue.get(True, 1)
                self.callback(item)
                CBTLOG.debug('CBT: Callback called with arg: {}'.format(item))
            except Queue.Empty:
                pass
        CBTLOG.info('CBT: Run stopped')

    def stop(self):
        """Stop the calling back"""
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


LUHLOG = logging.getLogger(__name__ + '.LiveUDPHandler')
LUHLOG.addHandler(logging.NullHandler())
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
        :param name: Return the name of the socket server
        """
        command = self.request[0]
        self.port = self.server.server_address[1]
        socket = self.request[1]
        LUHLOG.debug('Request \'{}\' received from {} on port {}'\
                     .format(command, self.client_address, self.port))

        if command == 'data':
            points = []
            for codename in DATA[self.port]['codenames']:
                points.append(DATA[self.port]['data'][codename])
            data = json.dumps(points)
        elif command == 'codenames':
            data = json.dumps(DATA[self.port]['codenames'])
        elif command == 'sane_interval':
            data = json.dumps(DATA[self.port]['sane_interval'])
        elif command == 'name':
            data = json.dumps(DATA[self.port]['name'])
        else:
            data = UNKNOWN_COMMAND

        socket.sendto(data, self.client_address)
        LUHLOG.debug('Sent back: \'{}\''.format(data))


LSLOG = logging.getLogger(__name__ + '.LiveSocket')
LSLOG.addHandler(logging.NullHandler())
class LiveSocket(CommonDataPullSocket):
    """This class implements a Live Socket"""

    def __init__(self, name, codenames, sane_interval, port=8000,
                 default_x=0, default_y=47):

        LSLOG.info('Initialize with: {}'.format(call_spec_string()))
        super(LiveSocket, self).__init__(
            name, codenames, port, default_x, default_y, None,
            init_timeouts=False, handler_class=LiveUDPHandler
        )
        # Set the type and the the sane_interval
        DATA[port]['type'] = 'live'
        DATA[port]['sane_interval'] = sane_interval

        # Initialize the last served data
        DATA[port]['last_served'] = {}
        for codename in codenames:
            DATA[port]['last_served'][codename] = (default_x, default_y)
        LSLOG.debug('Initilized')

    def set_point_now(self, codename, value):
        """Set the current y-value for codename using the current time as x
        
        :param codename: Name for the measurement whose current value should be
            set
        :type codename: str
        :param value: y-value
        :type value: float
        """
        self.set_point(codename, (time.time(), value))
        LSLOG.debug('Added time to value and called set_point')

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
        LSLOG.debug('Point {} for \'{}\' set'.format(tuple(point), codename))


#: The list of characters that are not allowed in code names
BAD_CHARS = ['#', ',', ';', ':']
#: The string returned if an unknown command is sent to the socket
UNKNOWN_COMMAND = 'UNKNOWN_COMMMAND'
#: The string used to indicate old or obsoleted data
OLD_DATA = 'OLD_DATA'
#: The answer prefix used when a push failed
PUSH_ERROR = 'ERROR'
#: The answer prefix used when a push succeds
PUSH_ACK = 'ACK'
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
#: The dict that transforms strings to convertion functions
TYPE_FROM_STRING = {'int': int, 'float': float, 'str': str,
                    'bool': bool_translate}