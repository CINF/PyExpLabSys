.. _drivers-doc-four_d_systems:

*********************
The 4d Systems module
*********************

Picaso Common
=============

The 4d Systems module at present contains the Picaso Common driver,
which at a minimum works for the Picaso uLCD-28PTU LCD display, but
likely will also work for other displays in the same series.

.. inheritance-diagram::
                         PyExpLabSys.drivers.four_d_systems.PicasoCommon
                         PyExpLabSys.drivers.four_d_systems.PicasouLCD28PTU

Usage Example
-------------

.. code-block:: python

    import time
    from PyExpLabSys.drivers.four_d_systems import PicasouLCD28PTU
    
    # Text example
    picaso = PicasouLCD28PTU(serial_device='/dev/ttyUSB0', baudrate=9600)
    picaso.clear_screen()
    for index in range(5):
        picaso.move_cursor(index, index)
        picaso.put_string('CINF')

    # Touch example
    picaso.move_cursor(7, 0)
    picaso.put_string('Try and touch me!')
    picaso.touch_set('enable')
    for _ in range(25):
        time.sleep(0.2)
        print picaso.touch_get_status()
        print picaso.touch_get_coordinates()
    
    picaso.close()

four_d_systems module
---------------------

.. automodule:: PyExpLabSys.drivers.four_d_systems
   :members:
   :member-order: bysource
   :show-inheritance:
   :private-members:
