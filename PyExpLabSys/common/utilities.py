"""This module contains various convinience functions for setting common things
up
"""

import logging
from logging.handlers import RotatingFileHandler


LOGGER_LEVELS = {'debug': logging.DEBUG,
                 'info': logging.INFO,
                 'warning': logging.WARNING,
                 'error': logging.ERROR,
                 'critical': logging.CRITICAL}


def get_logger(name, level='INFO', terminal_log=True, file_log=False,
               file_name=None, file_max_bytes=1048576, file_backup_count=3):
    """Set up the root logger and return a named logger with the same settings

    :param name: The name of the logger. E.g: 'Fancy logger script'
    :type name: str
    :param level: The level for the logger. Can be either 'DEBUG', 'INFO',
        'WARNING', 'ERROR' or 'CRITICAL'
    :type level: str
    :param terminal_log: If True then there should be logged to the terminal
    :type terminal_log: bool
    :param file_log: If True then logging to a file, with log rotation, will be
        activated. If ``file_name`` is not given, then ``name``.log will be
        used.
    :type file_log: bool
    :param file_name: File name to log to
    :type file_name: str
    :param file_max_size: The maximum size of the log file in bytes (default is
        1MB, which corresponds to roughly 10000 lines of log per file)
    :type file_max_size: int
    :param file_backup_count: The number of backup logs to keep (default is 3)
    :type file_backup_count: int
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
    logger = logging.getLogger('thetaprobe_pressure_logger')
    return logger
