
from PyExpLabSys.common.utilities import get_library_logger

log = get_library_logger(__name__, 'debug')


def myfunc():
    log.debug('debug message in myfunc')
