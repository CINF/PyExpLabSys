********
Overview
********

This page contains different overviews of the PyExpLabSys archive and
can work as an etry point for a new user.

Section :ref:`project_overview` contains a short listing of the
different components that PyExpLabSys consist of and the source code
and documentation entries that are relevant for that part.

The table in section :ref:`module_overview` contains an overview of
all the modules in PyExpLabSys. The overview consist of a short
description (the first line of the module docstring) and its Python
2/3 support status.

PyExpLabSys strive to support Python version 2.7 and >=3.3. See the section
:ref:`py3_support` about Python 3 support.

.. _project_overview:

Project Overview
================

Drivers
-------

At this point PyExpLabSys contains a reasonable amount of drivers (46
files, 81 classes May-16) for general purpose equipment (data cards,
temperature readout etc.) and for equipment related specifcally vacuum
lab we work in (pressure gauge controllers, mass spectrometers etc).

The source code for the drivers are in the `drivers
<https://github.com/CINF/PyExpLabSys/tree/master/PyExpLabSys/drivers>`_
folder, in which the file names are either manufacturer and model or
just the manufacturer.

The documentation for the drivers are divided into two sections
:ref:`drivers` and :ref:`drivers_autogen_only`. The latter is the
group for which there is only API documentation auto generated from
the source code and the former are the drivers that has more specific documentation with example usage etc.

File parsers
------------

PyExpLabSys also contains a small number of parsers for custom file
formats. The source code for these are in the `file_parsers
<https://github.com/CINF/PyExpLabSys/tree/master/PyExpLabSys/file_parsers>`_
folder and the documentation is in the :ref:`file-parsers` section.

Database Savers
---------------

TODO

Sockets
-------

TODO

Apps
----

TODO

Misc.
-----

.. _py3_support:

Python 3 support
================

**We love Python 3**. Unfortunately we are not hired to make software, but to keep a lab
running. This means that modules are only ported to Python 3, when it is either convinient or
we are touching the code anyway.

.. _module_overview:

Module Overview
===============

.. include:: py3_stat.inc

.. rubric:: Footnotes

.. [#inferred] For these modules the Python 2/3 status is not
	       indicated directly in the source code file and so the
	       status is inferred.
