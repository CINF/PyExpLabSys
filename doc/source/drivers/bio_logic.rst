.. _drivers-doc-bio_logic:

********************
The bio_logic module
********************

This module implements a driver for the SP-150 BioLogic potentiostat.

The implementation is built up around the notion of an instrument and
techniques. To communicate with the device, it is required to first create
an instrument, and then a technique and then load the technique onto the
instrument. This implementation was chosen because it closely reflects that
way the :ref:`specification <specification>` is written and the official ECLab
program is structured.

This driver communicates with the potentiostats via the EC-lib dll, which is
present in the ECLab development packages. This package must be installed
before the driver can be used. It can be downloaded `from the BioLogic website
<http://www.bio-logic.info/potentiostat-electrochemistry-ec-lab/downloads/software-upgrade-help/ec-lab-development-package/>`_.

See the :ref:`examples` sections some examples on how to use this driver.

See the :ref:`inheritance-diagram` for an inheritance diagram, that gives a
good overview over the available instruments and techniques.

 .. note:: See some important notes on 64 bit Windows and instruments series
           in the beginning of the :ref:`API documentation <API>`.

Implementation status and details
---------------------------------

There is a whole range of potentiostats (VMP2/VMP3, BiStat, VSP, SP-50/SP-150,
MGP2, HVP-803, SP-200, SP-300) that are covered by the same interface and
which therefore with very small adjustments could be supported by this module
as well. Currently only the SP-150 is implemented, because that is the only
one we have in-house. See the section :ref:`implement-new-potentiostat` for
details.

This module currently implements the handful of techniques that are used
locally (see a complete list at the top of the :ref:`module
documentation <API>`). It does however implement a :class:`.Technique` base class,
which does all the hard work of formatting the technique arguments correctly,
which means that writing a adding a new technique is limited to writing a new
class in which it is only required to specify which input arguments the
technique takes and which fields it outputs data.

.. _inheritance-diagram:

Inheritance diagram
===================

An inheritance diagram for the instruments and techniques (click the classes
to get to their API documentation):

.. py:currentmodule:: PyExpLabSys.drivers.bio_logic

.. inheritance-diagram:: SP150 CA CP CV CVA MIR OCV SPEIS

.. _examples:

Usage Example
-------------

The example below is a complete run-able file demonstrating how to use the
module, demonstrated with the OCV technique.

.. code-block:: python

 """OCV example"""

 from __future__ import print_function
 import time
 from PyExpLabSys.drivers.bio_logic import SP150, OCV


 def run_ocv():
     """Test the OCV technique"""
     ip_address = '192.168.0.257'  # REPLACE THIS WITH A VALID IP
     # Instantiate the instrument and connect to it
     sp150 = SP150(ip_address)
     sp150.connect()

     # Instantiate the technique. Make sure to give values for all the
     # arguments where the default values does not fit your purpose. The
     # default values can be viewed in the API documentation for the
     # technique.
     ocv = OCV(rest_time_T=0.2,
               record_every_dE=10.0,
               record_every_dT=0.01)

     # Load the technique onto channel 0 of the potentiostat and start it
     sp150.load_technique(0, ocv)
     sp150.start_channel(0)

     time.sleep(0.1)
     while True:
         # Get the currently available data on channel 0 (only what has
         # been gathered since last get_data)
         data_out = sp150.get_data(0)

         # If there is none, assume the technique has finished
         if data_out is None:
             break

         # The data is available in lists as attributes on the data
         # object. The available data fields are listed in the API
         # documentation for the technique.
         print("Time:", data_out.time)
         print("Ewe:", data_out.Ewe)

         # If numpy is installed, the data can also be retrieved as
         # numpy arrays
         #print('Time:', data_out.time_numpy)
         #print('Ewe:', data_out.Ewe_numpy)
         time.sleep(0.1)

     sp150.stop_channel(0)
     sp150.disconnect()

 if __name__ == '__main__':
     run_ocv()

This example covers how most of the techniques would be used. A noticeable
exception is the SPEIS technique, which returns data from two different
processes, on two different sets of data fields. It will be necessary to take
this into account, where the data is retrieved along these lines:

.. code-block:: python

 while True:
     time.sleep(0.1)
     data_out = sp150.get_data(0)
     if data_out is None:
         break

     print('Process index', data_out.process)
     if data_out.process == 0:
         print('time', data_out.time)
         print('Ewe', data_out.Ewe)
         print('I', data_out.I)
         print('step', data_out.step)
     else:
         print('freq', data_out.freq)
         print('abs_Ewe', data_out.abs_Ewe)
         print('abs_I', data_out.abs_I)
         print('Phase_Zwe', data_out.Phase_Zwe)
         print('Ewe', data_out.Ewe)
         print('I', data_out.I)
         print('abs_Ece', data_out.abs_Ece)
         print('abs_Ice', data_out.abs_Ice)
         print('Phase_Zce', data_out.Phase_Zce)
         print('Ece', data_out.Ece)
         # Note, no time datafield, but a t
         print('t', data_out.t)
         print('Irange', data_out.Irange)
         print('step', data_out.step)

For more examples of how to use the other techniques, see the `integration
test file on Github
<https://github.com/CINF/PyExpLabSys/blob/master/tests/integration_tests/test_bio_logic.py>`_

.. _specification:

External documentation
======================

The full documentation for the EC-Lab Development Package is available from
the BioLogic website `BioLogic Website
<http://www.bio-logic.info/potentiostat-electrochemistry-ec-lab/downloads/software-upgrade-help/ec-lab-development-package/>`_
and locally at CINF `on the wiki
<https://cinfwiki.fysik.dtu.dk/cinfwiki/Equipment#BioLogic_SP150>`_.

.. _implement-new-potentiostat:

Use/Implement a new potentiostat
================================

To use a potentiostat that has not already been implemented, there are
basically two options; :ref:`implement it <new-potentiostat-implement-it>` (3
lines of code excluding documentation) or :ref:`use the GeneralPotentiostat
class directly <new-potentiostat-use-general>`.

.. _new-potentiostat-implement-it:

Implement a new potentiostat
----------------------------

The SP150 class is implemented in the following manner::

 class SP150(GeneralPotentiostat):
     """Specific driver for the SP-150 potentiostat"""

     def __init__(self, address, EClib_dll_path=None):
         """Initialize the SP150 potentiostat driver

         See the __init__ method for the GeneralPotentiostat class for an
         explanation of the arguments.
         """
         super(SP150, self).__init__(
             type_='KBIO_DEV_SP150',
             address=address,
             EClib_dll_path=EClib_dll_path
         )

As it can be seen, the implementation of a new potentiostat boils down to:

* Inherit from :class:`.GeneralPotentiostat`
* Take ``address`` and ``EClib_dll_path`` as arguments to ``__init__``
* Call ``__init__`` from :class:`.GeneralPotentiostat` with the potentiostat
  type string and forward the ``address`` and ``EClib_dll_path``. The complete
  list of potentiostat type strings are listed in :data:`.DEVICE_CODES`.

.. _new-potentiostat-use-general:

Use ``GeneralPotentionstat``
----------------------------

As explained in :ref:`new-potentiostat-implement-it`, the only thing that is
required to use a new potentiostat is to call :class:`.GeneralPotentiostat`
with the appropriate potentiostat type string. As an alternative to
implementing the potentiostat in the module, this can of course also be done
directly. This example shows e.g. how to get a driver for the BiStat
potentiostat::

 from PyExpLabSys.drivers.bio_logic import GeneralPotentiostat
 potentiostat = GeneralPotentiostat(
     type_='KBIO_DEV_BISTAT',
     address='192.168.0.257',  # Replace this with a valid IP ;)
     EClib_dll_path=None
 )

The complete list of potentiostat type strings are listed in
:data:`.DEVICE_CODES`.

.. _implement-new-technique:

Use/Implement a new technique
=============================

To use a new technique, it will be required to implement it as a new
class. This can of course both be done directly in the module and contributed
back upstream or in custom code. The implementation of the OCV technique looks
as follows::

 class OCV(Technique):
     """Open Circuit Voltage (OCV) technique class.

     The OCV technique returns data on fields (in order):

     * time (float)
     * Ewe (float)
     * Ece (float) (only wmp3 series hardware)
     """

     #: Data fields definition
     data_fields = {
         'vmp3': [DataField('Ewe', c_float), DataField('Ece', c_float)],
         'sp300': [DataField('Ewe', c_float)],
     }

     def __init__(self, rest_time_T=10.0, record_every_dE=10.0,
                  record_every_dT=0.1, E_range='KBIO_ERANGE_AUTO'):
         """Initialize the OCV technique

         Args:
             rest_time_t (float): The amount of time to rest (s)
             record_every_dE (float): Record every dE (V)
             record_every_dT  (float): Record evergy dT (s)
             E_range (str): A string describing the E range to use, see the
                 :data:`E_RANGES` module variable for possible values
         """
         args = (
             TechnArg('Rest_time_T', 'single', rest_time_T, '>=', 0),
             TechnArg('Record_every_dE', 'single', record_every_dE, '>=', 0),
             TechnArg('Record_every_dT', 'single', record_every_dT, '>=', 0),
             TechnArg('E_Range', E_RANGES, E_range, 'in', E_RANGES.values()),
         )
         super(OCV, self).__init__(args, 'ocv.ecc')

As it can be seen, the new technique must inherit from
:class:`.Technique`. This base class is responsible for bounds checking of the
arguments and for formatting them in the appropriate way before sending them
to the potentiostat.

A class variable with a dict named ``data_fields`` must be defined, that
describes which data fields the technique makes data available at. See the
docstring for :class:`.Technique` for a complete description of what the
contents must be.

In the ``__init__`` method, the technique implementation must reflect all the
arguments the :ref:`specification <specification>` lists for the technique (in
this module, these arguments are made more Pythonic by; changing the names to
follow naming conventions except that symbols are still capital, infer the
number of arguments in lists instead of specifically asking for them and by
leaving out arguments that can only have one value). All of the arguments from
the :ref:`specification <specification>` must then be put, in order, into the
args tuple in the form the :class:`.TechniqueArgument` instances. The
specification for the arguments for the :class:`.TechniqueArgument` is in its
docstring.

Then, finally, :meth:`.Technique.__init__` is called via super, with the args
and the technique filename (is listed in the :ref:`specification
<specification>`) as arguments.

The last thing to do is to add an entry for the technique in the
:data:`.TECHNIQUE_IDENTIFIERS_TO_CLASS` dict, to indicate where the instrument
should look, to figure out what the data layout is, when it receives data from
this technique. If the new technique is implemented in stand alone code, this
will need to be hacked (see the attached example).

In :download:`this file<../_static/bio_logic_out_of_module_technique.py>` is a
complete (re)implementation of the OCV technique as it would look if it was
developed outside of the module.

.. _API:

bio_logic API
-------------

.. automodule:: PyExpLabSys.drivers.bio_logic
    :members:
    :member-order: bysource
    :private-members:
    :show-inheritance:
