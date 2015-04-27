"""This module contains a convenience function for easily setting up a
logger with the :py:mod:`logging` module.
"""

import sys
import inspect
import logging
import platform
import time
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
