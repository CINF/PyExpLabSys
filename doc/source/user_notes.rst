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

Using PyExpLabSys drivers outside of PyExpLabSys
================================================

TODO.
