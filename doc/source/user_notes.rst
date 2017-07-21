**********
User Notes
**********

This page has various different notes for using PyExpLabSys.

.. _user_notes_logging:

Setting up logging of your program
==================================

To set up logging of a program, it is possible to simply follow the `standard library
documentation <https://docs.python.org/3/howto/logging.html>`_. However, since many of the
programs that uses PyExpLabSys are programs that runs for extended periods without
monitoring, a more specific logging setup may be required. E.g. one that makes use of
email handlers, so be notified by email in case of errors or warnings.

For that purpose, PyExpLabSys has the :func:`.get_logger` function in the
:mod:`.utilities` module that is a convinience function to set up a logger with one or
more of the commonly used log handlers i.e. a terminal handler, a rotating file handler
and email handlers. This may be used to things up and running in a hurry.

.. code-block:: python

   from PyExpLabSys.common import utilities

   utilities.MAIL_HOST = 'my.mail.host'
   utilities.WARNING_EMAIL = 'email-address-to-use-in-case-of-warnings@log.com'
   utilities.ERROR_EMAIL = 'email-address-to-use-in-case-of-error@log.com'

   # Returns a logger with terminal and emails handlers per default
   LOG = utilities.get_logger('my_program_name')

   # A rotating file handler can be added:
   LOG = utilities.get_logger('my_program_name', file_log=True)
   
.. _user_notes_using_drivers_outside_pels:

Activating PyExpLabSys library logging in you program
=====================================================

PyExpLabSys contains quite a few loggers and exposes a few convinience
functions in the :mod:`.utilities` module for listing and activating them. To
get a list of loggers that are relevant for the modules that you have
imported, you can use either the :func:`.get_library_logger_names` function,
which will return you a list or the :func:`.print_library_logger_names`
function, which prints them out:

.. code-block:: python

   from PyExpLabSys.common import sockets
   from PyExpLabSys.common.utilities import print_library_logger_names

   print_library_logger_names()

produces the following output:

.. code-block:: text

    Current PyExpLabSys loggers
    ===========================
     * PyExpLabSys.common.sockets.PullUDPHandler
     * PyExpLabSys.common.sockets.DataPushSocket
     * PyExpLabSys.common.sockets.PushUDPHandler
     * PyExpLabSys.settings
     * PyExpLabSys.common.sockets.DateDataPullSocket
     * PyExpLabSys.common.sockets.CallBackThread
     * PyExpLabSys.common
     * PyExpLabSys.common.sockets.CommonDataPullSocket
     * PyExpLabSys.common.sockets
     * PyExpLabSys.common.sockets.DataPullSocket
     * PyExpLabSys
     * PyExpLabSys.common.sockets.LiveSocket

To activate a logger use the full path of the logger
e.g. ``PyExpLabSys.common.sockets.DataPullSocket`` and remembers that the
loggers are configured as a tree, so activating ``PyExpLabSys.common.sockets``
will activate all the loggers in that module and activating ``PyExpLabSys``
will activate all PyExpLabSys library loggers.

There are now two ways to activate a logger. One is to configure one from
scratch, using the path of the logger and the same options as in
:func:`get_logger`:

.. code-block:: python

    from PyExpLabSys.common import sockets
    from PyExpLabSys.common.utilities import activate_library_logging

    activate_library_logging(
        'PyExpLabSys.common.sockets.DateDataPullSocket',
        level='debug',
        file_log=True,
        file_name='socket_log.txt',
    )

This would output all log message at debug level to a file called
`socket_log.txt`.

The other way to activate a library logger is to ask it to enherit all the
handlers and levels from an existing logger. This will send all the library
log messages to the same destination:

.. code-block:: python

    from PyExpLabSys.common.utilities import get_logger, activate_library_logging
    from PyExpLabSys.common import sockets

    LOG = get_logger('my_program_name')
    LOG.info('My program started')

    # Configure a library logger to use the same handlers

    activate_library_logging(
        'PyExpLabSys.common.sockets.DateDataPullSocket',
        logger_to_inherit_from=LOG,
    )

It is still possible, when inheriting from an existing logger, to set a custom
level for the library logger, using the ``level`` argument as in the example
above.

Using PyExpLabSys drivers outside of PyExpLabSys
================================================

 *All I wanted was a banana, but what I got was a gorilla holding a banana*

The quote above, is often used to refer to the fact that it can be difficult to
use a component from a "framework" separate from the framework.

PyExpLabSys is not a framework as such, but there are some common elements that
are used across different in principle independent modules. Specifically, most
of the drivers in PyExpLabSys will work just fine outside of PyExpLabSys, with a
few very minor modifications, by just copying the file to where the driver is to
be used. Most of the drivers make use of just one other PyExpLabSys module that
tie it to the package, the :mod:`.supported_versions` module. The only thing
that this module does, is to mark the specific driver as working with Python 2,
Python 3 or both, and make a check at run-time of the Python version and
possibly output a warning. It can therefore trivially be removed. To do this,
look to lines of code somewhat like this:

.. code-block:: python

   from PyExpLabSys.common.supported_versions import python2_and_3
   python2_and_3(__file__)

and comment them out. The specific function that is imported and called, will
vary depending on which versions is supported, but that should be fairly simple
to figure out.
