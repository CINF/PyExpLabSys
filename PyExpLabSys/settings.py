"""This module contains the modules used for settings for PyExpLabSys

To use the settings module instantiate a :class:`.Settings` object and access the settings
as attributes::

    >>> from PyExpLabSys.settings import Settings
    >>> settings = Settings()
    >>> settings.util_log_max_emails_per_period
    5

The settings in the :class:`.Settings` are formed by 2 layers. The bottom layer are the
defaults, that are stored in the `PyExpLabSys/defaults.yaml
<https://github.com/CINF/PyExpLabSys/blob/master/PyExpLabSys/defaults.yaml>`_ file. Op top
of those are placed the user settings, that originate from the file whose path is in the
`settings.USERSETTINGS_PATH` variable. The user settings can me modified at run time as
opposed to having to write them to the user settings file before running. This is done
simply by writing to the properties on the settings object::

    >>> settings.util_log_max_emails_per_period = 7
    >>> settings.util_log_max_emails_per_period
    7

All :class:`.Settings` objects share the same settings, so these changes will be used when
using other parts of PyExpLabSys that makes use of one of the settings. Do however note,
that different parts of PyExpLabSys use the settings at different times (instantiate, call
etc.) so check with the documentation for each component when the settings needs to be
modified to take effect.

"""

# Implementation status
# =====================
# The following files has had settings incoorporated into them OR evaluated not to need
# them:
# common/sockets.py (Done)
# common/utilities.py (Implemented but may need refactoring)


from __future__ import print_function

import sys
import os
import logging
from threading import Lock
from os import path
from pprint import pformat
try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap
import codecs
import yaml


# WARNING. This module was written partially on November 9th, 2016,
# so somewhat distracted, expect bugs!


# Configure logging
LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


# Form path for defaults and user settings files
THISDIR = path.dirname(path.abspath(__file__))
DEFAULT_PATH = path.join(THISDIR, 'defaults.yaml')

# User settings
if os.environ.get('READTHEDOCS') == 'True':
    # Special case for read the docs
    USERSETTINGS_PATH = path.join(THISDIR, '..', 'bootstrap', 'user_settings.yaml')
else:
    # Krabbe is the sole responsible person for the MAC check, if it breaks bug him
    if sys.platform.lower().startswith('linux') or sys.platform.lower() == "darwin":
        USERSETTINGS_PATH = \
            path.join(path.expanduser('~'), '.config', 'PyExpLabSys', 'user_settings.yaml')
    else:
        USERSETTINGS_PATH = None


def value_str(obj):
    """Return a object and type str or NOT_SET if obj is None"""
    if obj is None:
        return 'NOT_SET'
    else:
        return '{} ({})'.format(obj, obj.__class__.__name__)


class Settings(object):
    """The PyExpLabSys settings object

    The settings are available to get and setable on this object as attributes i.e::

        >>> from PyExpLabSys.settings import Settings
        >>> settings = Settings()
        >>> settings.util_log_max_emails_per_period
        5

    The settings are stored as a ChainMap of the defaults and the user settings and this
    ChainMap object containing the current state of the settings is shared between all
    :class:`.Settings` objects.

    To get a list of all available settings see the :attr:`.Settings.settings_names`
    attribute. To get a pretty print of all settings names, types, default values, user
    setting values (if any) use the :meth:`.Settings.print_settings` method.

    """

    #: The settings ChainMap
    settings = None
    #: The available setting names
    settings_names = None
    # Access lock used to make sure the settings are consistent across threads
    _access_lock = Lock()
    
    def __init__(self):
        LOG.info('Init')
        with self._access_lock:
            if self.settings is None:
                self._load_settings()

    def _load_settings(self):
        """Load the defaults and user settings

        This is done when the first Settings object is instantiated
        """
        with open(DEFAULT_PATH, 'rb') as file_:
            default_settings = yaml.load(file_)
        LOG.info('Loaded defaults: %s', default_settings)

        user_settings = {}
        if os.path.isfile(USERSETTINGS_PATH) and os.access(USERSETTINGS_PATH, os.R_OK):
            try:
                with open(USERSETTINGS_PATH, 'rb') as file_:
                    user_settings = yaml.load(file_)
                LOG.info('Loaded user settings %s from path %s', user_settings,
                         USERSETTINGS_PATH)
            except Exception:
                LOG.exception('Exception during loading of user settings')
            # FIXME check user_settings keys
        else:
            LOG.info('No user settings found, file %s does not exist or is not readable',
                     USERSETTINGS_PATH)

        self.__class__.settings = ChainMap(user_settings, default_settings)
        self.__class__.settings_names = list(self.settings.keys())

    def __setattr__(self, key, value):
        """Set attribute"""
        with self._access_lock:
            if key in self.settings:
                self.settings[key] = value
            else:
                msg = 'Only settings that have a default can be set. They are:\n{}'
                # Pretty format the list of names in the exception
                raise AttributeError(msg.format(pformat(self.settings_names)))

    def __getattr__(self, key):
        """Get attribute"""
        with self._access_lock:
            if key in self.settings:
                value = self.settings[key]
            else:
                msg = 'Invalid settings name: {}. Available settings are:\n{}'
                # Pretty format the list of names in the exception
                raise AttributeError(msg.format(key, pformat(self.settings_names)))

            if value is None:
                msg = ('The setting "{}" is indicated in the defaults as *requiring* a '
                       'user setting before it can be used. Fill in the value in the '
                       'user settings file "{}" or instantiate a '
                       'PyExpLabSys.settings.Settings object and set the value there, '
                       '*before* attempting to use it.')
                raise AttributeError(msg.format(key, USERSETTINGS_PATH))

            return value


    def print_settings(self):
        """Pretty print of all default and user settings"""
        user_settings, default_settings = self.settings.maps
        print_template = '{{: <{}}}: {{: <{}}}  {{: <{}}}'

        # Calculate key length
        max_key_length = max(len(str(key)) for key in self.settings)

        # Form default values strings (w. type) and calculate max length
        default_strs = {k: value_str(v) for k, v in default_settings.items()}
        # The 7 is the length of NOT_SET and Default
        max_default_value_length = max(7, *[len(v) for v in default_strs.values()])

        # Form settings value strings (w. type) and calculate max length
        user_strs = {k: value_str(v) for k, v in user_settings.items()}
        # The 4 is the length of User
        max_settings_value_length = max(4, *[len(v) for v in user_strs.values()])

        # Format max lengths into print_template
        print_template = print_template.format(
            max_key_length, max_default_value_length, max_settings_value_length
        )

        # Printout the settings
        print('Settings')
        print(print_template.format('Key', 'Default', 'User'))
        print('=' * len(print_template.format('', '', '')))
        for key in sorted(self.settings.keys()):
            default = default_strs[key]
            print(print_template.format(key, default, user_strs.get(key, '')))
        

def main():
    """Main function used to simple testing"""
    #logging.basicConfig(level=logging.DEBUG)

    settings = Settings()

    print(settings.util_log_backlog_limit)
    settings.util_log_backlog_limit = 8
    print(settings.util_log_backlog_limit)
    print(settings.util_log_warning_email)
    print()
    settings.print_settings()
    

if __name__ == '__main__':
    main()
