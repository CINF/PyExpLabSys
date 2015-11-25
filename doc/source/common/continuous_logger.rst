.. _common-doc-loggers:

******************
The loggers module
******************

The logger module contains classes that hide some of all the repeated
code associated with sending data to the data base. The main component
is the :class:`.ContinousLogger` class, which is used to send
continuously logged data to the data base.

The continuous logger
=====================

The :class:`.ContinuousLogger` class is meant to do as much of the
manual work related to logging a parameter continuously to the
database as possible. The main features are:

* **Simple single method usage.** After the class is instantiated, a
  single call to :meth:`.enqueue_point` or :meth:`.enqueue_point_now`
  is all that is needed to log a point. No manual database query
  manipulation is required.
* **Resistent to network or database down time.** The class implements
  a queue for the data, from which points will only be removed if they
  are successfully handed of to the data base and while it is not
  possible to hand the data of, it will be stored in memory.

.. warning:: The resilience against network downtime has only been
             tested for the way it will fail if you disable the
             network from the machine it is running on. Different
             kinds of failures may produce different kinds of failure
             modes. If you encounter a failure mode that the class did
             not recover from you should report it as a bug.

.. todo:: Write that it uses new style database layout and refer to that section.

Usage Example
-------------

If code already exists to retrieve the data (e.g. a driver to interface a piece of equipment with), writing a data logger can be reduced to as little as the following:

.. code-block:: python

    from PyExpLabSys.common.loggers import ContinuousLogger
    
    db_logger = ContinuousLogger(table='dateplots_dummy',
                                 username='dummy', password='dummy',
                                 measurement_codenames = ['dummy_sine_one'])
    db_logger.start()

    # Initialize variable for the logging condition
    while True:
	new_value = driver.get_value()
	if contition_to_log_is_true:
	    db_logger.enqueue_point_now('dummy_sine_one', new_value)

or if it is preferred to keep track of the timestamp manually:

.. code-block:: python

    import time
    from PyExpLabSys.common.loggers import ContinuousLogger
    
    # Initiate the logger to write to the dateplots_dummy table, with usernam
    db_logger = ContinuousLogger(table='dateplots_dummy',
                                 username='dummy', password='dummy',
                                 measurement_codenames = ['dummy_sine_one'])
    db_logger.start()

    # Initialize variable for the logging condition
    while True:
	new_value = driver.get_value()
        now = time.time()
	if contition_to_log_is_true:
	    db_logger.enqueue_point('dummy_sine_one', (now, new_value))

Auto-generated module documentation
-----------------------------------

.. automodule:: PyExpLabSys.common.loggers
    :members:
    :member-order: bysource
    :show-inheritance:
