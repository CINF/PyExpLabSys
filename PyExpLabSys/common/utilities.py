"""This module contains a convenience function for easily setting up a
logger with the :py:mod:`logging` module.
"""

import logging
import platform
from logging.handlers import RotatingFileHandler, SMTPHandler


LOGGER_LEVELS = {'debug': logging.DEBUG,
                 'info': logging.INFO,
                 'warning': logging.WARNING,
                 'error': logging.ERROR,
                 'critical': logging.CRITICAL}


#: The email list warning emails are sent to
WARNING_EMAIL = 'pyexplabsys-warning@fysik.dtu.dk'
#: The email host used to send emails on logged warnings and errors
MAIL_HOST = 'mail.fysik.dtu.dk'
#: The email list error emails are sent to
ERROR_EMAIL = 'pyexplabsys-error@fysik.dtu.dk'


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
        """Cursom emit that checks if: warning =< level < error"""
        if logging.WARNING <= record.levelno < logging.ERROR:
            super(CustomSMTPWarningHandler, self).emit(record)
