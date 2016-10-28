.. _doc-combos:

*****************
The combos module
*****************

The combos are cobinations of other PyExpLabSys components in commonly used
configurations. Currently the only implemented combination are:

 * :class:`.LiveContinuousLogger` which combines a :class:`.LiveSocket` with a
   :class:`ContinuousDataSaver` and

.. contents:: Table of Contents
   :depth: 3


Examples
========

LiveContinuousLogger
--------------------

This example shows the case of using the combo to log values individually, using the "now"
variety of the method (:meth:`.LiveContinuousLogger.log_point_now`), which uses the time
now as the x-value:

.. code-block:: python

    from time import sleep
    from random import random
    from math import sin

    from PyExpLabSys.combos import LiveContinuousLogger

    # Initialize the combo and start it
    combo = LiveContinuousLogger(
        name='test',
        codenames=['dummy_sine_one', 'dummy_sine_two'],
        continuous_data_table='dateplots_dummy',
        username='dummy',
        password='dummy',
        time_criteria=0.1,
    )
    combo.start()

    # Measurement loop (typically runs forever, here just for 10 sec)
    for _ in range(10):
        # The two sine values here emulate a value to be logged
        sine_one = sin(random())
        sine_two = sin(random())
        combo.log_point_now('dummy_sine_one', sine_one)
        combo.log_point_now('dummy_sine_two', sine_two)
        sleep(1)

    combo.stop()

or if it is preferred to keep track of the timestamp manually, the
:meth:`.LiveContinuousLogger.log_point` method which can be used instead:

.. code-block:: python

    from time import sleep, time
    from math import sin, pi

    from PyExpLabSys.combos import LiveContinuousLogger

    # Initialize the combo and start it
    combo = LiveContinuousLogger(
        name='test',
        codenames=['dummy_sine_one', 'dummy_sine_two'],
        continuous_data_table='dateplots_dummy',
        username='dummy',
        password='dummy',
        time_criteria=0.1,
    )
    combo.start()

    # Measurement loop (typically runs forever, here just for 10 sec)
    for _ in range(10):
        # The two sine values here emulate a value to be logged
        now = time()
        sine_one = sin(now)
        sine_two = sin(now + pi)
        combo.log_point('dummy_sine_one', (now, sine_one))
        combo.log_point('dummy_sine_two', (now, sine_two))
        sleep(1)

    combo.stop()

Of course, like most of the underlying code, the combo also takes data at batches, as
shown in the following example (using :meth:`.LiveContinuousLogger.log_batch`):
    
.. code-block:: python

    from time import sleep, time
    from math import sin, pi

    from PyExpLabSys.combos import LiveContinuousLogger

    # Initialize the combo and start it
    combo = LiveContinuousLogger(
        name='test',
        codenames=['dummy_sine_one', 'dummy_sine_two'],
        continuous_data_table='dateplots_dummy',
        username='dummy',
        password='dummy',
        time_criteria=0.1,
    )
    combo.start()

    # Measurement loop (typically runs forever, here just for 10 sec)
    for _ in range(10):
        # The two sine values here emulate a value to be logged
        now = time()
        points = {
            'dummy_sine_one': (now, sin(now)),
            'dummy_sine_two': (now, sin(now + pi)),
        }
        combo.log_batch(points)
        sleep(1)

    combo.stop()


For the bacthes there is of course also a "now" variety
(:meth:`.LiveContinuousLogger.log_batch_now`), which there is no example for, but the
difference is same as for the single point/value.


Auto-generated module documentation
===================================

.. automodule:: PyExpLabSys.combos
    :members:
    :member-order: bysource
    :show-inheritance:
