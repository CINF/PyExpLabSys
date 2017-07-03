***************
Developer Notes
***************

This chapter contains information useful for developers of
PyExpLabSys. The documentation has the form of little sections that
each describe a small task.

.. contents:: Table of Contents
   :depth: 4

Setting up logging for a component of PyExpLabSys
=================================================

This section describes how to set up logging for a component in PyExpLabSys with the
:py:mod:`logging` module (i.e. the meaning of the word "logging" that refers to text
output of debug and status information to e.g. terminal and text files NOT sending data to
the database).

.. note:: This section specifically deals with setting up **logging for a component in
   PyExpLabSys, not of a program merely using PyExpLabSys**. For information about how to
   set up logging for a program merely using PyExpLabSys, see the `standard library
   documentation <https://docs.python.org/3/howto/logging.html>`_ and
   :ref:`user_notes_logging` for how to use some convenience functions in PyExpLabSys.

Setting up a logger for a component of PyExpLabSys should be done in
the manner recommended by the `standard library documentation for
logging from libraries
<https://docs.python.org/3/howto/logging.html#configuring-logging-for-a-library>`_. I.e. in
the beginning of the file to the following:

.. code-block:: python

   import logging
   LOG = logging.getLogger(__name__)
   LOG.addHandler(logging.NullHandler())

Where using ``__name__`` as the name, will ensure that it gets a name that is the full
qualified name of the module e.g. ``PyExpLabSys.common.utilities``.

If more fine grained logging is required, e.g. if a module consist of several large
classes and it would preferable with a logger per class, they can be set up in the same
manner. Such class loggers should keep the ``__name__`` as a prefix followed by a "." and
the name of the class, i.e:

.. code-block:: python

   # Assuming logging is already imported for the module logger
   MYCLASS_LOG = logging.getLogger(__name__ + '.MyClass')
   MYCLASS_LOG.addHandler(logging.NullHandler())

   class MyClass(object):
       """My fancy class"""
       pass

Editing/Updating Documentation
==============================

Adding a driver documentation stub for a new driver
---------------------------------------------------

After adding a new driver run the script:
``PyExpLabSys/doc/source/update-driver-only-autogen-stubs.py``. It
will generate driver documentation stubs for all the drivers that did
not previously have one. The stubs are placed in
``PyExpLabSys/doc/source/drivers-autogen-only``. After generating the
stubs add and commit the new stubs with git.

.. code-block:: bash

   cd PYEXPLABSYSPATH/doc/source
   python update-driver-only-autogen-stubs.py
   git add drivers-autogen-only/*.rst
   git cm "doc: Added new driver documentation stubs for <name of your driver>"

Adding additional documentation for a driver
--------------------------------------------

To add additional documentation for a driver, e.g. usage examples,
that is not well suited to be placed directly in the source file,
follow this procedure.

In the PyExpLabSys documentation the driver documentation files are
located in two different folders depending on whether it is a stub or
has extra documentation. To add extra documentation, first git move the
file and then start to edit and commit it as usual:

.. code-block:: bash

   cd PYEXPLABSYSPATH/doc/source
   git mv drivers-autogen-only/<name_of_your_driver_module>.rst drivers/
   # Edit and commit as usual


Writing Documentation
=====================

Hint: Disable Browser Cache
---------------------------

It is useful to disable caching in your browser temporarily, when it is being used to
preview local Sphinx pages. The easiest way to disable browser cache temporarily, is to
disable caching when the developer tools are open. For Firefox, the procedure is:

1. Open developer view (F12).
2. Open the settings for developer view (there is a little gear in the headline of
   developer view, third icon from the right)
3. Under "Advanced Settings" click "Disable Cache (when tool is open)"

In Chromium, the procedure is similar, except the check box is under "General".

Restructured Text Quick Reference
---------------------------------

General restructured text primer is located here: http://sphinx-doc.org/rest.html. Most of
the examples are from there. Super short summary of that follows:

Inline Markup and External Links
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**\*\*bold\*\***, *\*italics\**, ````code````.

External weblinks: ``http://xkcd.com/`` or with custom title ```Coolest comic ever
<http://xkcd.com/>`_``.

Sections
^^^^^^^^

The way to mark something as a section title is::

 #####
 parts
 #####

 ********
 chapters
 ********

 sections
 ========

 subsections
 -----------

 subsubsections
 ^^^^^^^^^^^^^^

 paragraphs
 """"""""""

The following is the convention for how to use those in PyExpLabSys and the overall
structure.

* ``index.rst``

  * Uses parts
  * includes the main table of contents that links to chapter files for common, drivers,
    apps etc.
  * ``common.rst`` (or any other chapter file)

    * Starts sections at chapter level
    * May include an additions table of contents tree for sub files
      e.g. common_contionuous_logger
    * ``common_contionuous_logger.rst``

      * Once again starts at chapter level

How these sections level work, I (Kenneth) must admit I have not investigated in
detail. It seems, that you can re-use section levels at a lower level in the document
hierarchy, if they are included in a table of contents tree, so we do. At some point it
would probably be good to try and understand that better

Labels and References
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: rst

   .. _my-reference-label:

   Section to Cross-Reference
   --------------------------

   References to its own section: :ref:`my-reference-label` or :ref:`Link title
   <my-reference-label>``


Source code blocks
^^^^^^^^^^^^^^^^^^

.. code-block:: rst

   .. code-block:: python

      import time
      t0 = time.time()
      # Stuff that takes time
      print(time.time() - t0)

Lists
^^^^^

.. code-block:: rst

   Bullet lists

   * Item over two lines. Item over two lines. Item over two lines.
     Item over two lines. Item over two lines. Item over two lines.

     * Lists can be nested, but must be separated by a blank line

   * Also when going back in level

   Numbered lists

   1. This is a numbered list.
   2. It has two items too.

   #. This is a numbered list.
   #. It has two items too.

References to code documentation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Examples
""""""""

* ``:py:class:`PyExpLabSys.common.sockets.DateDataPullSocket``` will create a link to the
  documentation like this: :py:class:`PyExpLabSys.common.sockets.DateDataPullSocket`
* ``:py:class:`~PyExpLabSys.common.sockets.DateDataPullSocket``` will shorten the link
  text to only the class name: :py:class:`~PyExpLabSys.common.sockets.DateDataPullSocket`
* ``:py:meth:`.close``` will make a link to the ``close`` method of the current class.
* ``:py:meth:`~.close``` as above using only 'close' as the link text
* ``:py:meth:`the close method <.close>``` will create a reference to the close method of
  the current class with the link text 'the close method'

Details
"""""""

In general cross references are: ``:role:`target``` or ``:role:`title <target>```

In this form, the role would usually be prefixed with a domain, so it could be
e.g. ``:py:func:`` to refer to a Python function. However, the ``py`` domain is the
default, so it can be dropped from the role (shortened form).

For Python the `relevant roles
<http://sphinx-doc.org/latest/domains.html#cross-referencing-python-objects>`_ (in
shortened form) are :

* ``:mod:`` for modules
* ``:func:`` for functions
* ``:data:`` for module level variables
* ``:class:`` for classes
* ``:meth:`` for methods
* ``:attr:`` for attributes
* ``:const:`` a "constant", a variable that is not supposed to be changed
* ``:exc:`` for exceptions
* ``:obj:`` for objects of unspecified type

Whatever is written as the target is `searched in the order
<http://sphinx-doc.org/latest/domains.html#cross-referencing-python-objects>`_:

1. Without any further qualification (directly importable I think)
2. Then with the current module preprended
3. Then with the current module and class (if any) preprended

If you prefix the target with a ``.``, then this `search order
<http://sphinx-doc.org/latest/domains.html#cross-referencing-syntax>`_ is reversed.

Prefixing the target with a ``~`` will shorten the link text to `only show the last
part <http://sphinx-doc.org/latest/domains.html#cross-referencing-syntax>`_.

Writing docstring with Napoleon
--------------------------------

The standard way of writing docstrings, with arguments definitions, in Sphinx is `quite
ugly <https://pythonhosted.org/an_example_pypi_project/sphinx.html#function-definitions>`_
and almost unreadable as pure text (which is annoying if you use an editor or IDE which
will show you the standard help-invoked documentation.

The `Napoleon <http://sphinxcontrib-napoleon.readthedocs.org/en/latest/>`_ extension to
Sphinx (`PyPi <https://pypi.python.org/pypi/sphinxcontrib-napoleon>`_ page) aims to fix
this by letting you write docstring in the `Google-style
<http://google.github.io/styleguide/pyguide.html>`_.

An example::

    def old_data(self, codename, timeout=900, unixtime=None):
        """Checks if the data for codename has timed out

        Args:
            codename (str): The codename whose data should be checked for
	        timeout
	Kwargs:
	    timeout (float): The timeout to use in seconds, defaults to 900s.
	    timestamp (float): Unix timestamp to compare to. Defaults to now.

	Raises:
	    ValueError: If codename is unknown
	    TypeError: If timeout or unixtime are not floats (or ints where appropriate)

        Returns:
            bool: Whether the data is too old or not
        """

A few things to note:

* Positional arguments, keyword arguments, exceptions and return values (Args, Kwargs,
  Raises, Returns) are written into sections. There are several aliases for each of them,
  but these are the recommended ones for PyExpLabSys (`all possibly sections
  <http://sphinxcontrib-napoleon.readthedocs.org/en/latest/#docstring-sections>`_).
* All are optional! Do not feel obligated to fill in Raises if it is not relevant.
* Args and kwargs are on the form: ``name (type): description``
* Raises and Returns (which has no name) are on the form: ``type: description``
* If the description needs to continue on the next line, it will need to be indented
  another level

The call signature for instantiation should be documented in ``__init__``.

In classes, attributes that are not defined explicitly with decorators, are documented in
the class docstring under the ``Attributes`` section::

    class MyClass(object):
        """Class that describes me

	Attributes:
	    name (str): The name of me
	    birthdate (float): Unix timestamp for my birthdate and time
	"""

	def __init__(self, name, birthdate):
	    """Initialize parameters"""
	    self.name = name
	    self.birthdate = birthdate

	@property
	def age(self):
	    """The approximate age of me in years"""
	    return (time.time() - self.birthdate) / (math.pi * 10**7)

A few things to notice:

* The attributes are listed in the same manner as arguments
* The age attribute, which is explicitely declared, will automatically be documented by
  its docstring
