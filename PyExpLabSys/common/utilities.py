"""This module contains a convenience function for easily setting up a
logger with the :py:mod:`logging` module.

This module uses the following settings from the :class:`.Settings` class:

 * util_log_warning_email
 * util_log_error_email
 * util_log_mail_host
 * util_log_max_emails_per_period (defaults to 5)
 * util_log_email_throttle_time (defaults to 86400s = 1day)
 * util_log_backlog_limit (defaults to 250)

 .. note:: All of these settings are at present read from the settings module at import
    time, so if it is desired to modify them at run time, it should be done before import

"""

from __future__ import unicode_literals, print_function

import sys
import inspect
import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
import platform
import time
from collections import deque

from ..settings import Settings

#: The :class:`.Settings` object used in this module
SETTINGS = Settings()

#: The email list warning emails are sent to
WARNING_EMAIL = SETTINGS.util_log_warning_email
#: The email list error emails are sent to
ERROR_EMAIL = SETTINGS.util_log_error_email
#: The email host used to send emails on logged warnings and errors
MAIL_HOST = SETTINGS.util_log_mail_host

# Limit emails to 5 of each kind per day, but send blocked emails along with
# the next allowed email
#: The maximum number of emails the logger will send in
#: :data:`.EMAIL_THROTTLE_TIME`
MAX_EMAILS_PER_PERIOD = SETTINGS.util_log_max_emails_per_period
EMAIL_TIMES = {
    logging.WARNING: deque([0] * MAX_EMAILS_PER_PERIOD, maxlen=MAX_EMAILS_PER_PERIOD),
    logging.ERROR: deque([0] * MAX_EMAILS_PER_PERIOD, maxlen=MAX_EMAILS_PER_PERIOD)
}
#: The time period that the numbers of emails will be limited within
EMAIL_THROTTLE_TIME = SETTINGS.util_log_email_throttle_time
#: The maximum number of messages in the email backlog that will be sent when
#: the next email is let through
EMAIL_BACKLOG_LIMIT = SETTINGS.util_log_backlog_limit
EMAIL_BACKLOG = {
    logging.WARNING: deque(maxlen=EMAIL_BACKLOG_LIMIT),
    logging.ERROR: deque(maxlen=EMAIL_BACKLOG_LIMIT),
}


### Log helpers
def _numeric_log_level_from_name(level_name):
    """Return a numeric log level from a log level name"""
    numeric_log_level = getattr(logging, level_name.upper(), None)
    if not isinstance(numeric_log_level, int):
        raise ValueError('Invalid logging level "{}"'.format(level_name))
    return numeric_log_level


# pylint: disable=too-many-arguments
def _create_handlers(name, terminal_log, file_log, file_name, file_max_bytes,
                     file_backup_count, email_on_warnings, email_on_errors):
    """Build and create common handlers

    Build and create the following common handler of requested:
     * A Stream handler
     * A rotating file handler
     * Email handlers

    """
    handlers = []

    # Create stream handler
    if terminal_log:
        handlers.append(logging.StreamHandler())

    # Create file handler
    if file_log:
        if file_name is None:
            file_name = name + '.log'
        file_handler = RotatingFileHandler(file_name, maxBytes=file_max_bytes,
                                           backupCount=file_backup_count)
        handlers.append(file_handler)

    # Create email warning handler
    if email_on_warnings:
        # Note, the placeholder in the subject will be replaced by the hostname
        warning_email_handler = CustomSMTPWarningHandler(
            mailhost=MAIL_HOST, fromaddr=WARNING_EMAIL,
            toaddrs=[WARNING_EMAIL], subject='Warning from: {}')
        warning_email_handler.setLevel(logging.WARNING)
        handlers.append(warning_email_handler)

    # Create email error handler
    if email_on_errors:
        # Note, the placeholder in the subject will be replaced by the hostname
        error_email_handler = CustomSMTPHandler(
            mailhost=MAIL_HOST, fromaddr=ERROR_EMAIL,
            toaddrs=[ERROR_EMAIL], subject='Error from: {}')
        error_email_handler.setLevel(logging.ERROR)
        handlers.append(error_email_handler)

    return handlers

### Public log functions
# pylint: disable=too-many-arguments, too-many-locals
def get_logger(name, level='INFO', terminal_log=True, file_log=False,
               file_name=None, file_max_bytes=1048576, file_backup_count=1,
               email_on_warnings=True, email_on_errors=True):
    """Setup and return a program logger

    This is meant as a logger to be used in a top level program/script. The logger is set
    up for with terminal, file and email handlers if requested.

    Args:
        name (str): The name of the logger, e.g: 'my_fancy_program'. Passing in an empty
            string will return the root logger. See note below.
        level (str): The level for the logger. Can be either ``'DEBUG'``,
            ``'INFO'``, ``'WARNING'``, ``'ERROR'`` or ``'CRITICAL'``. See
            :py:mod:`logging` for details. Default is ``'INFO'``.
        terminal_log (bool): If ``True`` then logging to a terminal will be
            activated. Default is ``True``.
        file_log (bool): If ``True`` then logging to a file, with log rotation,
            will be activated. If ``file_name`` is not given, then
            ``name + '.log'`` will be used. Default is ``False``.
        file_name (str): Optional file name to log to
        file_max_size (int): The maximum size of the log file in bytes. The
            default is ``1048576`` (1MB), which corresponds to roughly 10000
            lines of log per file.
        file_backup_count (int): The number of backup logs to keep. The default
            is ``1``.
        email_on_warnings (bool): Whether to send an email to the
            :data:`.WARNING_EMAIL` email list if a warning is logged. The
            default is ``True``.
        email_on_error (bool): Whether to send en email to the
            :data:`.ERROR_EMAIL` email list if an error (or any logging level
            above) is logged. The default is ``True``.

    Returns:
        :py:class:`logging.Logger`: A logger module with the requested setup

    .. note:: Passing in the empty string as the ``name``, will return the root logger.
       That means that all other `library loggers
       <https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library>`_
       will inherit the level and handlers from this logger, which may potentially result
       in **a lot** of output. See :func:`.activate_library_logging` for a way to activate
       the library loggers from PyExpLabSys in a more controlled manner.

    """
    # Get a named logger and set the level
    logger = logging.getLogger(name)
    numeric_log_level = _numeric_log_level_from_name(level)
    logger.setLevel(numeric_log_level)

    # Get handlers
    handlers = _create_handlers(
        name=name, terminal_log=terminal_log, file_log=file_log, file_name=file_name,
        file_max_bytes=file_max_bytes, file_backup_count=file_backup_count,
        email_on_warnings=email_on_warnings, email_on_errors=email_on_errors,
    )

    # Add formatters to the handlers and add the handlers to the root_logger
    formatter = logging.Formatter('%(asctime)s:%(name)s: %(levelname)s: %(message)s')
    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def get_library_logger_names():
    """Return all loggers currently configured in PyExpLabSys"""
    logger = logging.getLogger()
    # Somewhat undocumented way of getting all the loggers, let's hope it never changes
    logger_names = logger.manager.loggerDict.keys()
    pyexplabsys_loggers = [ln for ln in logger_names if ln.startswith('PyExpLabSys')]
    return pyexplabsys_loggers


def print_library_logger_names():
    """Nicely printout all loggers currently configured in PyExpLabSys"""
    print('Current PyExpLabSys loggers')
    print('===========================')
    for log_name in get_library_logger_names():
        print(" *", log_name)


def activate_library_logging(logger_name, logger_to_inherit_from=None, level=None,
                             terminal_log=True, file_log=False, file_name=None,
                             file_max_bytes=1048576, file_backup_count=1,
                             email_on_warnings=True, email_on_errors=True):
    """Activate logging for a PyExpLabSys library logger

    Args:
        logger_name (str): The name of the logger to activate, as returned by
            :func:`.get_library_logger_names`
        logger_to_inherit_from (logging.Logger): (Optional) If this is set, the library
            logger will simply share the handlers that are present in this logger. The
            library to be activated will also inherit the level from this logger, unless
            ``level`` is set, in which case it will override. In case neither ``level``
            nor the level on ``logger_to_inherit_from`` is set, the level will not be
            changed.
        level (str): (Optional) See docstring for :func:`.get_logger`. If
            ``logger_to_inherit_from`` is not set, it will default to 'info'.
        terminal_log (bool): See docstring for :func:`.get_logger`
        file_log (bool): See docstring for :func:`.get_logger`
        file_name (str): See docstring for :func:`.get_logger`
        file_max_size (int): See docstring for :func:`.get_logger`
        file_backup_count (int): See docstring for :func:`.get_logger`
        email_on_warnings (bool): See docstring for :func:`.get_logger`
        email_on_error (bool): See docstring for :func:`.get_logger`
    """
    # Get hold of the logger to activate
    if logger_name not in get_library_logger_names():
        message = ('The logger "{}" is not among the currently configured PyExpLabSys '
                   'library loggers. Make sure you import the relevant PyExpLabSys '
                   'module *before* activating it. To get a list of all PyExpLabSys '
                   'library loggers call get_library_logger_names function from this '
                   'module')
        raise ValueError(message.format(logger_name))
    logger = logging.getLogger(logger_name)

    # Activate by inheriting handlers and level
    if logger_to_inherit_from is not None:
        # Set level for library logger
        if level is not None:
            numeric_log_level = _numeric_log_level_from_name(level)
            logger.setLevel(numeric_log_level)
        elif logger_to_inherit_from.level > 0:
            logger.setLevel(logger_to_inherit_from.level)

        # Inherit all the handlers
        for handler in logger_to_inherit_from.handlers:
            logger.addHandler(handler)
        return

    # Get level and set
    if level is None:
        # Set default
        level = 'info'
    numeric_log_level = _numeric_log_level_from_name(level)
    logger.setLevel(numeric_log_level)

    # Create handlers
    handlers = _create_handlers(
        name=logger_name, terminal_log=terminal_log, file_log=file_log, file_name=file_name,
        file_max_bytes=file_max_bytes, file_backup_count=file_backup_count,
        email_on_warnings=email_on_warnings, email_on_errors=email_on_errors,
    )

    # Set formatter and add handler
    formatter = logging.Formatter('%(asctime)s:%(name)s: %(levelname)s: %(message)s')
    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)


### Custom handler classes
class CustomSMTPHandler(SMTPHandler):
    """PyExpLabSys modified SMTP handler"""

    def emit(self, record):
        """Custom emit that throttles the number of email sent"""
        email_log = EMAIL_TIMES[self.level]
        email_backlog = EMAIL_BACKLOG[self.level]
        now = time.time()

        # Get the time of the oldest email
        oldest_email_time = min(email_log)
        # If the oldest email was sent more than throttle time ago, allow this
        # one through
        if oldest_email_time < (now - EMAIL_THROTTLE_TIME):
            email_log.append(now)
            # If there is a backlog, add it to the message before sending
            if len(email_backlog) > 0:
                backlog = '\n'.join(email_backlog)
                # Explicitly convert record.msg to str to allow for
                # logging.exception() with exception as arg instead of msg
                record.msg = str(record.msg) + '\n\nBacklog:\n' + backlog
                email_backlog.clear()

            super(CustomSMTPHandler, self).emit(record)
        else:
            email_backlog.append(self.formatter.format(record))

    def getSubject(self, record):
        """Returns subject with hostname"""
        base_subject = super(CustomSMTPHandler, self).getSubject(record)
        try:
            hostname = platform.node()
        # pylint: disable=broad-except
        except Exception:
            hostname = 'Unknown'

        return base_subject.format(hostname)


class CustomSMTPWarningHandler(CustomSMTPHandler):
    """Custom SMTP handler to emit record only if: warning =< level < error"""

    def emit(self, record):
        """Custom emit that checks if: warning =< level < error"""
        if logging.WARNING <= record.levelno < logging.ERROR:
            super(CustomSMTPWarningHandler, self).emit(record)


### Random utils
def call_spec_string():
    """Return the argument names and values of the method or function it was
    called from as a string

    Returns:
        str: The argument string, e.g:
            (name='hello', codenames=['aa', 'bb'], port=8000)
    """
    # pylint: disable=protected-access
    frame = sys._getframe(1)
    argvals = inspect.getargvalues(frame)
    if argvals.args[0] == 'self':
        return inspect.formatargvalues(argvals.args[1:], *argvals[1:])
    else:
        return inspect.formatargvalues(*argvals)
