"""Functions used to indicate and check for supported Python versions"""

from __future__ import print_function
import os
import sys
import warnings

DOCRUN = os.environ.get('READTHEDOCS') == 'True' or 'sphinx' in sys.modules

# We support 2.7 and above (which will never happen) or 3.3 and above
PY2_MIN_VERSION = (2, 7)
PY3_MIN_VERSION = (3, 3)

# Check for valid versions
VERSION = sys.version_info
PY2_CHECK = VERSION.major == PY2_MIN_VERSION[0] and VERSION.minor >= PY2_MIN_VERSION[1]
PY3_CHECK = VERSION.major == PY3_MIN_VERSION[0] and VERSION.minor >= PY3_MIN_VERSION[1]
PY2_OR_3_CHECK = PY2_CHECK or PY3_CHECK

# Warnings texts
WARNING2OR3 = ('\n'
    '========================================================================\n'
    '# The module: \'{filepath}\'\n'
    '# only supports Python {0}.{1} or above in the Python {0} series.\n'
    '# Your milages may vary!!!\n'
    '========================================================================\n'
)
WARNING2AND3 = ('\n'
    '========================================================================\n'
    '# The module: \'{filepath}\'\n'
    '# only supports Python {0}.{1} or above in the Python {0} series\n'
    '# OR Pythons {2}.{3} or above in the Python {2} series.\n'
    '# Your milages may vary!!!\n'
    '========================================================================\n'
)


def python2_only(filepath):
    """Print out a warning if the Python version is not in the supported range of Python 2
    versions (>=2.7)
    """
    if PY2_CHECK:
        return
    if not DOCRUN:
        warnings.warn(WARNING2OR3.format(*PY2_MIN_VERSION, filepath=filepath))


def python3_only(filepath):
    """Print out a warning if the Python version is not in the supported range of Python 3
    versions (>=3.3)
    """
    if PY3_CHECK:
        return
    if not DOCRUN:
        warnings.warn(WARNING2OR3.format(*PY3_MIN_VERSION, filepath=filepath))


def python2_and_3(filepath):
    """Print out a warning if the Python version is not in the supported range of Python 2 or 3
    versions (>=2.7 or >=3.3)
    """
    if PY2_OR_3_CHECK:
        return
    if not DOCRUN:
        warnings.warn(WARNING2AND3.format(*PY2_MIN_VERSION + PY3_MIN_VERSION, filepath=filepath))


# Mark this file as being Python 2 and 3 compatible
python2_and_3(__file__)


if __name__ == '__main__':
    python2_only(__file__)
    python3_only(__file__)
    python2_and_3(__file__)
