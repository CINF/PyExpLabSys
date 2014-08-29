******************
The sockets module
******************

The data sockets are convenience classes that make it easier to send
data back and forth between machines. All the data sockets are socket
**servers**, i.e. they handle requests, and to interact with them it
is necessary to work as a client. The main purpose these sockets is to
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

In the following examples it is assumed that all other code that is
needed, such as e.g. an equipment driver, already exists and the
places where such code is needed is filled in with dummy code.


DateDataPullSocket make data available (network variable)
---------------------------------------------------------

Making data available on the network for pulling can be achieved with:

.. code-block:: python

    from PyExpLabSys.common.sockets import DateDataPullSocket
    
    # Create a data socket with timeouts and start the socket server
    name = 'Last shot usage data from the giant laser on the moon'
    codenames = ['moon_laser_power', 'moon_laser_duration']
    socket = DateDataPullSocket(name, codename, timeouts = [1.0, 0.7])
    socket.start()

    try:
        while True:
	    power, duration = laser.get_values()
	    # To set a variable use its codename
	    socket.set_point_now('moon_laser_power', power)
	    socket.set_point_now('moon_laser_duration', duration)
    except KeyboardInterrupt:
        # Stop the socket server
        socket.stop()

or if it is preferred to keep track of the timestamp manually:

.. code-block:: python

    try:
        while True:
	    now = time.time()
	    power, duration = driver.get_values()
	    socket.set_point('moon_laser_power', (now, power))
	    socket.set_point('moon_laser_duration', (now, duration))
    except KeyboardInterrupt:
        # Stop the socket server
        socket.stop()

A few things to note from the examples. The port number used for the
socket is 9000 which is the default for this type is socket, see
:ref:`port-defaults`. The two measurements have been setup to have
different timeouts (maximum ages), but it could also be set up to be
the same and if it is the same it can be supplied as just one float
instead of a list of floats. For the sockets, the codenames should be
kept short, but for data safety reasons should contain an unambiguous
reference to the setup.


DataPushSocket, send data (network variable)
--------------------------------------------

To receive data on a machine, the :class:`.DataPushSocket` can be
used. To set it up simply to be able to see the last received data and
the updated total data, set it up like this:

.. code-block:: python

    from PyExpLabSys.common.sockets import DataPushSocket
    name = 'Command receive socket for giant laser on the moon'
    dps = DataPushSocket(name, action='store_last')
    # Get data
    timestamp_last, last = dps.last
    timestamp_updated, updated = dps.updated
    # ... do whatever and stop socket
    dps.stop()

After settings this up, the last received data set will be available
in the :attr:`.DataPushSocket.last` property. ``last_timestamp`` is a
Unix timestamp of last reception and last is a dictionary with the
last received data (all data sent to the :class:`.DataPushSocket` is
in dictionary form, see :meth:`.PushUDPHandler.handle` for
details). Alternatively, the :attr:`.DataPushSocket.updated` property
contains the last value received value for each key in dict received
ever (i.e. not only in the last transmission).


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

As seen above, the queue that holds the data items is available as the
:attr:`.DataPushSocket.last` attribute. Data can be pulled out by
calling ``get()`` on the queue. NOTE: The for-loop only gets all the
data that was available at the time of calling ``qsize()``, so if the
actions inside the for loop takes time, it is possible that new data
will be enqueued while the for-loop is running, which it will not pull
out.

If it is desired to use an existing queue or to set up a queue with
other than default settings, the :class:`.DataPushSocket` can be
instatiated with a custom queue.


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


DataPushSocket, control class and send return values back (callback with return)
--------------------------------------------------------------------------------

This is reduced version of an example in which an entire class is controlled via the :class:`.DataPushSocket`:

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
    

This socket would then be sent commands in the form of JSON encoded dicts from an UDP client in the secret lair. These dicts could look like:

.. code-block:: python

    {'method': 'update_settings', 'power': 300, 'focus': 10}
    # or
    {'method': 'state', 'state': 'active'}
    
which would, respectively, make the ``update_settings`` method be called with the arguments ``power=300, focus=10`` and the ``state`` method be called with the argument ``state='active'``. NOTE: In this implementation it is the responsibility of the caller that the method name exists and that the arguments that are sent have the correct names. An alternative but less flexible way to do the same, would be to make an if-elif-else structure on the method name and format the arguments in manually:

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

The complete and running example of both server and client for this
example can be downloaded in these two files: :download:`server <_static/laser_control_server.py>`, :download:`client <_static/laser_control_client.py>`.

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

Auto-generated module documentation
===================================

.. automodule:: PyExpLabSys.common.sockets
    :members:
    :member-order: bysource
    :special-members:
    :show-inheritance:
