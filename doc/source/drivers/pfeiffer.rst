.. _drivers-doc-pfeiffer:

*******************
The pfeiffer module
*******************

The pfeiffer module contains drivers for equipment from Pfeiffer
Vacuum. At present the module contains drivers for the :class:`TPG 261
<.TPG261>` and :class:`TPG 262 <.TPG262>` pressure measurement and
control units.

TPG 26x
=======

The TPG 261 and TPG 262 has the same communications protocol and
therefore the driver has been implemented as a common driver in the
:class:`.TPG26x` class, which the :class:`.TPG261` and
:class:`.TPG262` classes inherit from, as illustrated below.

.. inheritance-diagram:: PyExpLabSys.drivers.pfeiffer 

The driver implements only a sub set of the specification, but given
that the ground work has already been done, it should be simple to
implement more methods as they are needed.

Usage Example
-------------

The driver classes can be instantiated by specifying just the address
of the serial communications port the unit is connected to:

.. code-block:: python

    from PyExpLabSys.drivers.pfeiffer import TPG262
    tpg = TPG262(port='/dev/ttyUSB0')
    value, (status_code, status_string) = tpg.pressure_gauge(1)
    # or
    value, _ = tpg.pressure_gauge(1)
    unit = tpg.pressure_unit()
    print 'pressure is {} {}'.format(value, unit)

If the baud rate on the TPG 26x unit has been changed away from the
default setting of 9600, then the correct baud rate will need to be
given as a parameter.

pfeiffer module
---------------

.. automodule:: PyExpLabSys.drivers.pfeiffer
   :members:
   :member-order: bysource
   :show-inheritance:
