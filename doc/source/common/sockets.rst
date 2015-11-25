.. _common-doc-sockets:

******************
The sockets module
******************

The data sockets are convenience classes that make it easier to send
data back and forth between machines. All the data sockets are socket
**servers**, i.e. they handle requests, and to interact with them it
is necessary to work as a client. The main purpose of these sockets is to
hide the complexity and present a easy-to-use interface while
performing e.g. error checking in the background.

The sockets are divided into push and pull sockets, which are intended
to either pull data from or pushing data to.

The main advantages of the **pull sockets** are:

* **Simple usage**: After e.g. the :class:`.DateDataPullSocket` or
  :class:`.DataPullSocket` class is instantiated, a single call to the
  ``set_point`` method is all that is needed to make a point available
  via the socket.
* **Codename based**: After instantiation, the different data slots
  are referred to by codenames. This makes code easier to read and
  help to prevent e.g. indexing errors.
* **Timeout safety to prevent serving obsolete data**: The class can
  be instantiated with a timeout for each measurement type. If the
  available point is too old an error message will be served.

The main advantages of the **push socket** are:

* **Simple usage**: If all that is required is to receive data in a
  variable like manner, both the last and the updated variable values
  can be accessed via the :attr:`.DataPushSocket.last` and
  :attr:`.DataPushSocket.updated` properties.
* **Flexible**: The :class:`.DataPushSocket` offers a lot of
  functionality around what actions are performed when a data set is
  received, including enqueue it or calling a callback function with
  the data set as an argument.

.. contents:: Table of Contents
   :depth: 3


Examples
========

In the following examples it is assumed, that all other code that is
needed, such as e.g. an equipment driver, already exists, and the
places where such code is needed, is filled in with dummy code.

.. _pull-example:

DateDataPullSocket make data available (network variable)
---------------------------------------------------------

Making data available on the network for pulling can be achieved with:

.. code-block:: python

    from PyExpLabSys.common.sockets import DateDataPullSocket
    
    # Create a data socket with timeouts and start the socket server
    name = 'Last shot usage data from the giant laser on the moon'
    codenames = ['moon_laser_power', 'moon_laser_duration']
    moon_socket = DateDataPullSocket(name, codenames, timeouts=[1.0, 0.7])
    moon_socket.start()

    try:
        while True:
	    power, duration = laser.get_values()
	    # To set a variable use its codename
	    moon_socket.set_point_now('moon_laser_power', power)
	    moon_socket.set_point_now('moon_laser_duration', duration)
    except KeyboardInterrupt:
        # Stop the socket server
        moon_socket.stop()

or if it is preferred to keep track of the timestamp manually:

.. code-block:: python

    try:
        while True:
	    now = time.time()
	    power, duration = driver.get_values()
	    moon_socket.set_point('moon_laser_power', (now, power))
	    moon_socket.set_point('moon_laser_duration', (now, duration))
    except KeyboardInterrupt:
        # Stop the socket server
        moon_socket.stop()

A few things to note from the examples. The port number used for the socket is
9000, which is the default for this type is socket (see
:ref:`port-defaults`). The two measurements have been setup to have different
timeouts (maximum ages), which is in seconds by the way, but it could also be
set up to be the same, and if it is the same, it can be supplied as just one
float ``timeouts=0.7`` instead of a list of floats. For the sockets, the
codenames should be kept relatively short, but for data safety reasons, they
should contain an unambiguous reference to the setup, i.e. the 'moon_laser'
part.

.. _pull-client-side:

Client side
^^^^^^^^^^^

The client can be set up in the following manner::

  import socket
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  # hostname can something like 'rasppi250', if that happens to be the one
  # located on the moon
  host_port = ('moon_raspberry_pi', 9000)

.. _pull-command-and-data-examples:

Command and data examples
^^^^^^^^^^^^^^^^^^^^^^^^^

With the initialization of the client as above, it is now possible to send the
socket different commands and get appropriate responses. In the following, the
different commands are listed, along with how to send it, receive (and decode)
the reply.

The ``name`` command
""""""""""""""""""""

Used to get the name of the socket server, which can be used to make sure that
data is being pulled from the correct location::

  command = 'name'
  sock.sendto(command, host_port)
  data = sock.recv(2048)

at which point the data variable, which contains the reply, will contain the
string ``'Last shot usage data from the giant laser on the moon'``.

The ``json_wn`` command
"""""""""""""""""""""""

.. tip:: The 'wn' suffix is short for 'with names' and is used for all the
   sockets to indicate that data is sent or received prefixed with names of the
   particular data channel

This command is used to get all the latest data encoded as :py:mod:`json`. It
will retrieve all the data as a dictionary where the keys are the names,
encoded as :py:mod:`json` for transport::

  import json
  command = 'json_wn'
  sock.sendto(command, host_port)
  data = json.loads(sock.recv(2048))

at which point the data variable will contain a dict like this one::

  {u'moon_laser_power': [1414150015.697648, 47.0], u'moon_laser_duration': [1414150015.697672, 42.0]}

The ``codenames_json`` and ``json`` commands
""""""""""""""""""""""""""""""""""""""""""""

It is also possible to decouple the codenames. A possible use case might be to
produce a plot of the data. In such a case, the names are really only needed
when setting up the plot, and then afterwards the data should just arrive in
the same order, to add points to the graph. This is exactly what these two
command do::

  import json
  
  # Sent only once
  command = 'codenames_json'
  sock.sendto(command, host_port)
  codenames = json.loads(sock.recv(2048))

  # Sent repeatedly
  command = 'json'
  sock.sendto(command, host_port)
  data = json.loads(sock.recv(2048))

after which the codenames variable would contain a list of codenames::

  [u'moon_laser_power', u'moon_laser_duration']

and the data variable would contain a list of points, returned in the same
order as the codenames::

  [[1414150538.551638, 47.0], [1414150538.551662, 42.0]]

The ``codename#json`` command
"""""""""""""""""""""""""""""

.. note:: The codename in the command should be substituted with an actual codename

It is also possible to ask for a single point by name.::

  import json
  command = 'moon_laser_power#json'
  sock.sendto(command, host_port)
  data = json.loads(sock.recv(2048))

At which point the data variable would contains just a single point as a list::

  [1414151366.400581, 47.0]

The ``raw_wn``, ``codenames_raw``, ``raw`` and ``codename#raw`` commands
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

These commands do exactly the same as their :py:mod:`json` counterparts, only
that the data is not encoded as :py:mod:`json`, but with the homemade raw
encoding.

.. _raw-warning:
.. warning:: The raw encoding is manually serialized, which is an 100% guarantied
	     error prone approach, so use the :py:mod:`json` variant whenever
	     possible. Even Labview® to some extent `supports json
	     <http://zone.ni.com/reference/en-XX/help/371361K-01/glang/flat_unflat_string/>`_
	     as of version 2013.

Remember that when receiving data in the raw encoding, it should not be json
decoded, so the code to work with these commands will look like this::

  command = 'some_raw_command'  # E.g. raw_wn
  sock.sendto(command, host_port)
  data = sock.recv(2048)

There format if the raw encoding is documented in the API documentation for the
:meth:`.PullUDPHandler.handle` method.

Below are a simple list of each type of raw command and example out::

  command = 'raw_wn'
  # Output
  'moon_laser_power:1414154338.17,47.0;moon_laser_duration:1414154338.17,42.0'

  command = 'codenames_raw'
  # Output
  'moon_laser_power,moon_laser_duration'

  command = 'raw'
  # Output
  '1414154433.4,47.0;1414154433.4,42.0'

  command = 'moon_laser_power#raw'
  # Output
  '1414154485.08,47.0'
  

DataPushSocket, send data (network variable)
--------------------------------------------

To receive data on a machine, the :class:`.DataPushSocket` can be
used. To set it up simply to be able to see the last received data and
the updated total data, set it up like this:

.. code-block:: python

    from PyExpLabSys.common.sockets import DataPushSocket
    name = 'Data receive socket for giant laser on the moon'
    dps = DataPushSocket(name, action='store_last')
    # Get data
    timestamp_last, last = dps.last
    timestamp_updated, updated = dps.updated
    # ... do whatever and stop socket
    dps.stop()

After settings this up, the last received data set will be available as a tuple
in the :attr:`.DataPushSocket.last` property, where the first value is the Unix
timestamp of reception and the second value is a dictionary with the last
received data (all data sent to the :class:`.DataPushSocket` is in dictionary
form, see :meth:`.PushUDPHandler.handle` for details). Alternatively, the
:attr:`.DataPushSocket.updated` property contains the last value received ever
for each key in the dict (i.e. not only in the last transmission).

.. _push-network-variable-command-examples:

Command examples
^^^^^^^^^^^^^^^^

The socket server understands commands in two formats, a :py:mod:`json` and a
raw encoded one. For details about how to send commands to a socket server and
receive the reply in the two different encodings, see the sections
:ref:`pull-client-side` and :ref:`pull-command-and-data-examples` from the
:ref:`pull-example` section.

The :py:mod:`json` commands looks like this:

.. code-block:: text

 json_wn#{"greeting": "Live long and prosper", "number": 47}
 json_wn#{"number": 42}

After the first command the data values in both the
:attr:`.DataPushSocket.last` and the :attr:`.DataPushSocket.updated` properties
are::

 {u'greeting': u'Live long and prosper', u'number': 47}

After the second command the value in the :attr:`.DataPushSocket.last` property
is::

 {u'number': 42}

and the value in the :attr:`.DataPushSocket.updated` property is::

 {u'greeting': u'Live long and prosper', u'number': 42}

The commands can also be raw encoded, in which case the commands above will be:

.. code-block:: text

 raw_wn#greeting:str:Live long and prosper;number:int:47
 raw_wn#number:int:42

.. warning :: See the :ref:`warning about the raw encoding <raw-warning>`.

Upon receipt, the socket server will make a message available on the socket,
that contains a status for the receipt and a copy of the data it has gathered
(in simple Python string representation). I will look like this:

.. code-block:: text

  ACK#{u'greeting': u'Live long and prosper', u'number': 47}

If it does not understand the data, e.g. if it is handed badly formatted raw
data, it will return an error:

.. code-block:: text

  Sending: "raw_wn#number:88"
  Will return: "ERROR#The data part 'number:88' did not match the expected format of 3 parts divided by ':'"
  
  Sending: "raw_wn#number:floats:88"
  Will return: "ERROR#The data type 'floats' is unknown. Only ['int', 'float', 'bool', 'str'] are allowed"

DataPushSocket, see all data sets received (enqueue them)
---------------------------------------------------------

To receive data and make sure that each and every point is reacted to,
it is possible to ask the socket to enqueue the data. It is set up in
the following manner:

.. code-block:: python

    from PyExpLabSys.common.sockets import DataPushSocket
    name = 'Command receive socket for giant laser on the moon'
    dps = DataPushSocket(name, action='enqueue')
    queue = dps.queue  # Local variable to hold the queue
    # Get on point
    print queue.get()
    # Get all data
    for _ in range(queue.qsize()):
        print queue.get()
    # ... do whatever and stop socket
    dps.stop()

As seen above, the queue that holds the data items, is available as the
:attr:`.DataPushSocket.queue` attribute. Data can be pulled out by calling
``get()`` on the queue. NOTE: The for-loop only gets all the data that was
available at the time of calling ``qsize()``, so if the actions inside the for
loop takes time, it is possible that new data will be enqueued while the
for-loop is running, which it will not pull out.

If it is desired to use an existing queue or to set up a queue with
other than default settings, the :class:`.DataPushSocket` can be
instantiated with a custom queue.

Command examples
^^^^^^^^^^^^^^^^

Examples of commands that can be sent are the same as in the :ref:`code example
above <push-network-variable-command-examples>`, after which the queue would
end up containing the two dictionaries::

 {u'greeting': u'Live long and prosper', u'number': 47}
 {u'number': 42}

DataPushSocket, make socket call function on reception (callback)
-----------------------------------------------------------------

With the :class:`.DataPushSocket` it is also possible to ask the
socket to call a callback function on data reception:

.. code-block:: python

    from PyExpLabSys.common.sockets import DataPushSocket
    import time

    # Module variables
    STATE = 'idle'
    STOP = False

    def callback_func(data):
        """Callback function for the socket"""
	print 'Received: {}'.format(data)
	#... do fancy stuff depending on the data, e.g. adjust laser settings
	# or fire (may change STATE)

    name = 'Command callback socket for giant laser on the moon'
    dps = DataPushSocket(name, action='callback_async', callback=callback_func)

    while not STOP:
	# Check if there is a need for continuous activity e.g. monitor
	# temperature of giant laser during usage
	if STATE == 'fire':
	    # This function should end when STATE changes away from 'fire'
	    monitor_temperature()
        time.sleep(1)

    # After we are all done, stop the socket
    dps.stop()

In this examples, the data for the callbacks (and therefore the
callbacks themselves) will be queued up and happen
asynchronously. This makes it possible to send a batch of commands
without waiting, but there is no monitoring of whether the queue is
filled faster than it can be emptied. It can of course be checked by
the user, but if there is a need for functionality in which the
sockets make such checks itself and rejects data if there is too much
in queue, then talk to the development team about it.

Command examples
^^^^^^^^^^^^^^^^

Command examples this kind of socket will as always be dicts, but in this case
will likely have to contain some information about which action to perform or
method to call, but that is entirely up to the user, since that is implemented
by the user in the call back function. Some examples could be:

.. code-block:: text

  json_wn#{"action": "fire", "duration": 8, "intensity": 300}
  json_wn#{"method": "fire", "duration": 8, "intensity": 300}

DataPushSocket, control class and send return values back (callback with return)
--------------------------------------------------------------------------------

This is reduced version of an example that shows two things:

 * How to get the return value when calling a function via the
   :class:`.DataPushSocket`
 * How to control an entire class with a :class:`.DataPushSocket`

.. code-block:: python

    from PyExpLabSys.common.sockets import DataPushSocket

    class LaserControl(object):
        """Class that controls the giant laser laser on the moon"""

        def __init__(self):
            self.settings = {'power': 100, 'focus': 100, 'target': None}
            self._state = 'idle'

	    # Start socket
            name = 'Laser control, callback socket, for giant laser on the moon'
            self.dps = DataPushSocket(name, action='callback_direct',
                                      callback=self.callback)
            self.dps.start()

	    self.stop = False
	    # Assume one of the methods can set stop
            while not self.stop:
		# Do continuous stuff on command
                time.sleep(1)
            self.dps.stop()

        def callback(self, data):
            """Callback and central control function"""
	    # Get the method name and don't pass it on as an argument
            method_name = data.pop('method')
	    # Get the method
            method = self.__getattribute__(method_name)
	    # Call the method and return its return value
            return method(**data)

        def update_settings(self, **kwargs):
            """Update settings"""
            for key in kwargs.keys():
                if key not in self.settings.keys():
                    message = 'Not settings for key: {}'.format(key)
                    raise ValueError(message)
            self.settings.update(kwargs)
            return 'Updated settings with: {}'.format(kwargs)
    
        def state(self, state):
            """Set state"""
            self._state = state
            return 'State set to: {}'.format(state)
    

This socket would then be sent commands in the form of :py:mod:`json` encoded
dicts from an UDP client in the secret lair. These dicts could look like:

.. code-block:: python

    {'method': 'update_settings', 'power': 300, 'focus': 10}
    # or
    {'method': 'state', 'state': 'active'}
    
which would, respectively, make the ``update_settings`` method be called with
the arguments ``power=300, focus=10`` and the ``state`` method be called with
the argument ``state='active'``. NOTE: In this implementation, it is the
responsibility of the caller that the method name exists and that the arguments
that are sent have the correct names. An alternative, but less flexible, way to
do the same, would be to make an if-elif-else structure on the method name and
format the arguments in manually:

.. code-block:: python

    def callback(self, data):
        """Callback and central control function"""
        method_name = data.get('method')
	if method_name == 'state':
	    if data.get('state') is None:
	        raise ValueError('Argument \'state\' missing')
	    out = self.state(data['state'])
        elif method_name == 'update_settings':
	    # ....
	    pass
	else:
	    raise ValueError('Unknown method: {}'.format(method_name))

        return out

The complete and running example of both server and client for this example can
be downloaded in these two files: :download:`server
<../_static/laser_control_server.py>`, :download:`client
<../_static/laser_control_client.py>`.

Command examples
^^^^^^^^^^^^^^^^

See the attached files with example code for command examples.

.. _port-defaults:

Port defaults
=============

To make for easier configuration on both ends of the network
communication, the different kinds of sockets each have their own
default port. They are as follows:

============================ ============
Socket                       Default port
============================ ============
:class:`.DateDataPullSocket` 9000
:class:`.DataPullSocket`     9010
:class:`.DataPushSocket`     8500
:class:`.LiveSocket`         8000
============================ ============

Again, to ease configuration also on the client side, if more than one
socket of the same kind is needed on one machine, then it is
recommended to simply add 1 to the port number for each additional
socket.

Inheritance
===========

The :class:`DateDataPullSocket` and :class:`DataPullSocket` classes inherit
common functionality, such as;

* Input checks
* Initialization of DATA
* Methods to start and stop the thread and reset DATA

from the :class:`CommonDataPullSocket` class, as illustrated in the
diagram below.

.. inheritance-diagram:: PyExpLabSys.common.sockets

Status of a socket server
=========================

All 4 socket servers understand the ``status`` command. This command will
return some information about the status of the machine the socket server is
running on and the status of **all** socket servers running on this
machine. The reason the command returns the status for all the socket servers
running on the machine is, that what this command is really meant for, is to
get the status of *the system* and so it should not be necessary to communicate
with several socket servers to get that.

The data returned is a :py:mod:`json` encoded dictionary, which looks like
this:

.. code-block:: python

  {u'socket_server_status':
            {u'8000': {u'name': u'my_live_socket',
                       u'since_last_activity': 0.0009279251098632812,
                       u'status': u'OK',
                       u'type': u'live'},
             u'9000': {u'name': u'my_socket',
                       u'since_last_activity': 0.0011229515075683594,
                       u'status': u'OK',
                       u'type': u'date'}},
   u'system_status':
            {u'filesystem_usage': {u'free_bytes': 279182213120,
                                   u'total_bytes': 309502345216},
             u'last_apt_cache_change_unixtime': 1413984912.529932,
             u'last_git_fetch_unixtime': 1413978995.4109764,
             u'load_average': {u'15m': 0.14, u'1m': 0.1, u'5m': 0.15},
             u'max_python_mem_usage_bytes': 37552128,
             u'number_of_python_threads': 3,
             u'uptime': {u'idle_sec': 321665.77,
                         u'uptime_sec': 190733.39}}}

Socket server status
--------------------

The **socket servers status** is broken down into one dictionary for each
socket server, indexed by their ports. The status for the individual socket
server comprise of the following items:

:name (*str*): The name of the socket server
:since_last_activity (*float*): The number of seconds since last activity on
    the socket server
:status (*str*): The status of the socket server. It will return either
    ``'OK'`` if the last activity was newer than the activity timeout, or
    ``'INACTIVE'`` if the last activity was older than the activity timeout or
    ``'DISABLED'`` is activity monitoring is disabled for the socket server.
:type: The type of the socket server

System status
-------------

The **system status** items depends on the operating system the socket server
is running on.

All operating systems
^^^^^^^^^^^^^^^^^^^^^

:last_git_fetch_unixtime (*float*): The Unix timestamp of the last git fetch of
    the 'origin' remote, which points at the `Github archive
    <https://github.com/CINF/PyExpLabSys>`_
:max_python_mem_usage_bytes (*int*): The maximum memory usage of Python in bytes
:number_of_python_threads (*int*): The number of Python threads in use

Linux operating systems
^^^^^^^^^^^^^^^^^^^^^^^

:uptime (*dict*): Information about system uptime (from ``/proc/uptime``). The
    value ``'uptime_sec'`` contains the system uptime in seconds and the value
    ``'idle_sec'`` contains the idle time in seconds. NOTE: While the uptime is
    measured in wall time, the idle time is measured in CPU time, which means
    that if the system is multi-core, it will add up idle time for all the
    cores.
:last_apt_cache_change_unixtime (*float*): The Unix time stamp of the last
   change to the apt cache, which should be a fair approximation to the last
   time the system was updated
:load_average(*dict*): The load average (roughly number of active processes)
    over the last 1, 5 and 15 minutes (from ``/proc/loadavg``). For a detailed
    explanation see `the /proc/loadavg section from the proc man-page
    <http://linux.die.net/man/5/proc>`_
:filesystem_usage (*dict*): The number of total and free bytes for the
    file-system the PyExpLabSys archive is located on

Auto-generated module documentation
===================================

.. automodule:: PyExpLabSys.common.sockets
    :members:
    :member-order: bysource
    :show-inheritance:
