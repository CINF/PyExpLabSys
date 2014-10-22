"""This module contains a convenience function for easily setting up a
logger with the :py:mod:`logging` module.
"""

import sys
import os
import inspect
import logging
import platform
import time
import resource
import threading
from collections import deque
from logging.handlers import RotatingFileHandler, SMTPHandler


#: The email list warning emails are sent to
WARNING_EMAIL = 'pyexplabsys-warning@fysik.dtu.dk'
#: The email list error emails are sent to
ERROR_EMAIL = 'pyexplabsys-error@fysik.dtu.dk'
#: The email host used to send emails on logged warnings and errors
MAIL_HOST = 'mail.fysik.dtu.dk'

# Limit emails to 5 of each kind per day, but send blocked emails along with
# the next allowed email
#: The maximum number of emails the logger will send in
#: :data:`.EMAIL_THROTTLE_TIME`
MAX_EMAILS_PER_PERIOD = 5
EMAIL_TIMES = {
    logging.WARNING:
    deque([0] * MAX_EMAILS_PER_PERIOD, maxlen=MAX_EMAILS_PER_PERIOD),
    logging.ERROR:
    deque([0] * MAX_EMAILS_PER_PERIOD, maxlen=MAX_EMAILS_PER_PERIOD)
}
#: The time period that the numbers of emails will be limited within
EMAIL_THROTTLE_TIME = 24 * 60 * 60
#: The maximum number of messages in the email backlog that will be sent when
#: the next email is let through
EMAIL_BACKLOG_LIMIT = 250
EMAIL_BACKLOG = {logging.WARNING: deque(maxlen=EMAIL_BACKLOG_LIMIT),
                 logging.ERROR: deque(maxlen=EMAIL_BACKLOG_LIMIT)}


# pylint: disable=too-many-arguments, too-many-locals
def get_logger(name, level='INFO', terminal_log=True, file_log=False,
               file_name=None, file_max_bytes=1048576, file_backup_count=3,
               email_on_warnings=True, email_on_errors=True):
    """Set up the root logger and return a named logger with the same settings

    Args:
        name (str): The name of the logger, e.g: 'fancy_logger_script'
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
            is ``3``.
        email_on_warnings (bool): Whether to send an email to the
            :data:`.WARNING_EMAIL` email list if a warning is logged. The
            default is ``True``.
        email_on_error (bool): Whether to send en email to the
            :data:`.ERROR_EMAIL` email list if an error (or any logging level
            above) is logged. The default is ``True``.

    Returns:
        :py:class:`logging.Logger`: A logger module with the requested setup
    """
    # Get the root logger and set the level
    log_level = getattr(logging, level.upper())
    root_logger = logging.getLogger('')
    root_logger.setLevel(log_level)

    handlers = []
    # Form the handler(s) and set the level
    if terminal_log:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(log_level)
        handlers.append(stream_handler)

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

    # Create rotating file handler
    if file_log:
        if file_name is None:
            file_name = name + '.log'
        file_handler = RotatingFileHandler(file_name, maxBytes=file_max_bytes,
                                           backupCount=file_backup_count)
        file_handler.setLevel(log_level)
        handlers.append(file_handler)

    # Add formatters to the handlers and add the handlers to the root_logger
    formatter = logging.Formatter(
        '%(asctime)s:%(name)s: %(levelname)s: %(message)s')
    for handler in handlers:
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Create a named logger and return it
    logger = logging.getLogger(name)
    return logger


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
                # Explicitely convert record.msg to str to allow for
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


def call_spec_string():
    """Return the argument names and values of the method or function it was
    called from as a string

    Returns:
        str: The argument string, e.g:
            (name='hallo', codenames=['aa', 'bb'], port=8000)
    """
    # pylint: disable=protected-access
    frame = sys._getframe(1)
    argvals = inspect.getargvalues(frame)
    if argvals.args[0] == 'self':
        return inspect.formatargvalues(argvals.args[1:], *argvals[1:])
    else:
        return inspect.formatargvalues(*argvals)


class SystemStatus(object):
    """Class that fetches set of system status information"""

    def __init__(self):
        # Form the list of which items to measure on different platforms
        self.platform = sys.platform
        self.all_list = ['last_git_fetch', 'max_python_mem_usage_bytes',
                         'number_of_python_threads']
        if self.platform == 'linux2':
            self.all_list += ['uptime', 'last_apt_cache_change_unixtime',
                              'load_average', 'filesystem_usage']

    def complete_status(self):
        """Returns all system status information items as a dictionary"""
        all_items = {}
        for item in self.all_list:
            all_items[item] = getattr(self, item)()
        return all_items

    # All platforms
    def last_git_fetch(self):
        """Returns the unix timestamp and author time zone offset in seconds of
        the last git commit
        """
        # Get dirname of current file and add two parent directory entries a
        # .git and a FETCH_HEAD in a hopefullt crossplatform manner, result:
        # /home/pi/PyExpLabSys/PyExpLabSys/common/../../.git/FETCH_HEAD
        fetch_head_file = os.path.join(
            os.path.dirname(__file__),
            *[os.path.pardir] * 2 + ['.git', 'FETCH_HEAD']
        )
        # Check for last change
        if os.access(fetch_head_file, os.F_OK):
            return os.path.getmtime(fetch_head_file)
        else:
            return None

    @staticmethod
    def max_python_mem_usage_bytes():
        """Returns the python memory usage"""
        pagesize = resource.getpagesize()
        this_process = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        children = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        return (this_process + children) * pagesize

    @staticmethod
    def number_of_python_threads():
        """Returns the number of threads in Python"""
        return threading.activeCount()

    # Linux only
    @staticmethod
    def uptime():
        """Returns the system uptime"""
        sysfile = '/proc/uptime'
        if os.access(sysfile, os.R_OK):
            with open(sysfile, 'r') as file_:
                # Line looks like: 10954694.52 10584141.11
                line = file_.readline()
            names = ['uptime_sec', 'idle_sec']
            values = [float(value) for value in line.split()]
            return dict(zip(names, values))
        else:
            return None

    @staticmethod
    def last_apt_cache_change_unixtime():
        """Returns the unix timestamp of the last apt-get upgrade"""
        apt_cache_dir = '/var/cache/apt'
        if os.access(apt_cache_dir, os.F_OK):
            return os.path.getmtime('/proc/uptime')
        else:
            return None

    @staticmethod
    def load_average():
        """Returns the system load average"""
        sysfile = '/proc/loadavg'
        if os.access(sysfile, os.R_OK):
            with open(sysfile, 'r') as file_:
                line = file_.readline()
            # The line looks like this:
            # 0.41 0.33 0.26 1/491 21659
            loads = (float(load) for load in line.split()[0:3])
            return dict(zip(['1m', '5m', '15m'], loads))
        else:
            return None

    @staticmethod
    def filesystem_usage():
        """Return the total and free number of bytes in the current filesystem
        """
        statvfs = os.statvfs(__file__)
        status = {
            'total_bytes': statvfs.f_frsize * statvfs.f_blocks,
            'free_bytes': statvfs.f_frsize * statvfs.f_bfree
        }
        return status
