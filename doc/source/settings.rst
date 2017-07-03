.. _doc-settings:

*******************
The settings module
*******************

Settings for PyExpLabSys component are handled via the :class:`.Settings` class in the
:mod:`settings` module.

Getting started
===============

To use the settings module instantiate a :class:`.Settings` object and access the settings
as attributes::

    >>> from PyExpLabSys.settings import Settings
    >>> settings = Settings()
    >>> settings.util_log_max_emails_per_period
    5

User settings can be modified at run time simply by assigning a new value to the
attributes::

    >>> settings.util_log_max_emails_per_period = 7
    >>> settings.util_log_max_emails_per_period
    7

Details
=======

The settings are handled in two layers; **defaults** and **user settings**.

The defaults are stored in the `PyExpLabSys/defaults.yaml
<https://github.com/CINF/PyExpLabSys/blob/master/PyExpLabSys/defaults.yaml>`_ file.

.. note:: It is not possible to write to a setting that does not have a default

.. note:: In the defaults, a value of ``null`` is used to indicate a settings that must be
   overwritten by a user setting before any modules tries to use it.

The user settings are stored in a user editable file. The path used is stored in the
`settings.USERSETTINGS_PATH` variable.  On Linux system the user settings path is
``~/.config.PyExpLabSys.user_settings.yaml``.

.. note:: If the value is None, it means that your operating system is not yet supported
   by the sett ings module. This should be reported as an issue on Github.

All :class:`.Settings` objects share the same settings, so changes made via one object
will be used everywhere, in fact that is what makes it possible to modify settings at
runtime (as shown above). **Do however note, that different modules reads the settings at
different points in time. Some will read them when an object from that module is
instantiated and others will read them at module import time**. That means, that for some
modules it will be necessary to modify the settings before the rest of the PyExpLabSys
modules is imported, in order to be able to modify them at runtime. At which point in time
the settings are read should be stated in the module documentation.


Auto-generated module documentation
===================================

.. automodule:: PyExpLabSys.settings
    :members:
    :member-order: bysource
    :show-inheritance:
