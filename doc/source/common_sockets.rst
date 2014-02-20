
******************
The sockets module
******************

.. automodule:: PyExpLabSys.common.sockets

The DateDataSocket class
========================

.. autoclass:: PyExpLabSys.common.sockets.DateDataSocket
    :members:
    :special-members:

Usage example
-------------

If code already exists to retrieve the data (e.g. a driver to
interface a piece of equipment with), making the date date available via teh socket can be reduced to as little as the following:

.. code-block:: python

    from PyExpLabSys.common.sockets import DateDataSocket
    
    # Create a data socket with timeouts
    socket = DateDataSocket(['s1m1', 's1m2'], timeouts = [1.0, 0.7])
    # Start the socket server
    socket.start()

    # Main loop
    try:
        while True:
	    new_value1, new_value2 = driver.get_values()
	    socket.set_point_now('s1m1', new_value1)
	    socket.set_point_now('s1m2', new_value2)
    except KeyboardInterrupt:
        # Stop the socket server
        socket.stop()

or if it is preferred to keep track of the timestamp manually:

.. code-block:: python

    import time
    from PyExpLabSys.common.sockets import DateDataSocket
    
    # Create a data socket with timeouts
    socket = DateDataSocket(['s1m1', 's1m2'], timeouts = [1.0, 0.7])
    # Start the socket server
    socket.start()

    # Main loop
    try:
        while True:
	    now = time.time()
	    new_value1, new_value2 = driver.get_values()
	    socket.set_point('s1m1', (now, new_value1))
	    socket.set_point('s1m2', (now, new_value2))
    except KeyboardInterrupt:
        # Stop the socket server
        socket.stop()

A few things to note from the examples:

* If no port number is given to the `__init__` method, the socket will
  be formed on the default port 9000
* The two measurements have been setup to have different timeouts
  (maximum ages), but it could also be set up to be the same
* For the sockets, the codenames are purposely kept sort, to minimize
  network load. However, for safety, they should include a reference to
  the setup and the type so e.g. a *temperature* measurement on the
  *dummy* setup could be named *dum_t*.


The data UDP handler
====================

DataUDPHandler class
--------------------

.. autoclass:: PyExpLabSys.common.sockets.DataUDPHandler
    :members:
    :special-members:
