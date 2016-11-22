# pylint: disable=too-many-ancestors

r"""Complete serial driver for the Tenma 72-2535, \*72-2540, \*72-2545, \*72-2550, 72-2930
and \*72-2940 (see details below)

 .. note:: \* The driver has not been tested on the models with a \*. However, the two
    models that has been tested, seems like are built from the same template, so there is
    a very high probability that the generic :class:`.TenmaBase` driver will work with
    those as well.

Implemented according to "Series Protocol V2.0 of Remote Control" (referred to in inline
comments as the spec) which can be downloaded from the link below.

Manual and specification can be downloaded from here: `https://www.element14.com/community/
docs/DOC-75108/l/protocol-information-for-tenma-72-2550-and-tenma-72-2535-qa-window-
driver <https://www.element14.com/community/docs/DOC-75108/l/protocol-information-for-
tenma-72-2550-and-tenma-72-2535-qa-window-driver>`_

"""

from __future__ import unicode_literals, print_function

import logging
from time import sleep, time
from functools import wraps

from serial import Serial

from PyExpLabSys.common.supported_versions import python2_and_3
# Mark this module as supporting both Python 2 and 3
python2_and_3(__file__)

# Setup logging
LOG = logging.getLogger(__name__)
LOG.addHandler(logging.NullHandler())


class TenmaBase(Serial):
    r"""Serial driver for the Tenma 72-2535, \*72-2540, \*72-2545, \*72-2550, 72-2930 and
    \*72-2940 power supplies

    .. note:: \* The driver has not been tested on the models with a \*. However, the two
       models that has been tested, seems like are built from the same template, so there
       is a very high probability that the generic :class:`.TenmaBase` driver will work
       with those as well.

    """

    def __init__(self, device, sleep_after_command=0.1):
        """Initialize driver

        Args:
            device (str): The serial device to connect to e.g. COM4 or /dev/ttyUSB0
            sleep_after_command (float): (Optional) The time to sleep after sending a
                command, to make sure that the device is ready for another one. Defaults
                to 0.1, but quick tests suggest that 0.05 might be enough.
        """
        LOG.info('%s init on device: %s, sleep_after_command=%s', self.__class__.__name__,
                 device, sleep_after_command)
        super(TenmaBase, self).__init__(device)
        self.sleep_after_command = sleep_after_command

    def com(self, command, decode_reply=True):
        """Send command to the device and possibly return reply

        Args:
            command (str): Command as unicode object
            decode_reply (bool): (Optional) Whether the reply should be utf-8 decoded to
                return a unicode object
        """
        LOG.debug('Send command: %s', command)
        self.write(command.encode('utf-8'))
        sleep(self.sleep_after_command)
        if command.endswith('?'):
            reply = self.read(self.in_waiting)
            if decode_reply:
                reply = reply.decode('utf-8')  # pylint: disable=redefined-variable-type
                LOG.debug('Got (utf-8) decoded reply: %s', repr(reply))
            else:
                LOG.debug('Got reply: %s', repr(reply))
            return reply

    # Spec command 1
    def set_current(self, current):
        """Sets the current setpoint

        Args:
            current (float): The current to set
        """
        LOG.debug('set_current called with: %s', current)
        self.com('ISET1:{:.3f}'.format(current))

    # Spec command 2
    def get_current(self):
        """Return the current setpoint

        Returns:
            float: The current setpoint
        """
        LOG.debug('get_current called')
        current_reply = self.com('ISET1?')
        return float(current_reply.strip())

    # Spec command 3
    def set_voltage(self, voltage):
        """Sets the voltage setpoint

        Args:
            voltage (float): The voltage to set
        """
        LOG.debug('set_voltage called with: %s', voltage)
        self.com('VSET1:{:.2f}'.format(voltage))

    # Spec command 4
    def get_voltage(self):
        """Return the voltage setpoint


        Returns:
            float: The voltage setpoint
        """
        LOG.debug('get_voltage called')
        voltage_reply = self.com('VSET1?')
        return float(voltage_reply.strip())

    # Spec command 5
    def get_actual_current(self):
        """Return the actual_current

        Returns:
            float: The actual current
        """
        LOG.debug('get_actual_current called')
        current_reply = self.com('IOUT1?')
        return float(current_reply.strip())

    # Spec command 6
    def get_actual_voltage(self):
        """Return the actual voltage

        Returns:
            float: The actual coltage
        """
        LOG.debug('get_actual_voltage called')
        voltage_reply = self.com('VOUT1?')
        return float(voltage_reply.strip())

    # Spec command 7
    def set_beep(self, on_off):
        """Turn the beep on or off

        on_off (bool): The beep status to set
        """
        LOG.debug('set_beep called with: %s', on_off)
        self.com('BEEP' + ('1' if on_off else '0'))

    # Spec command 8
    def set_output(self, on_off):
        """Turn the output of or off

        on_off (bool): The otput status to set
        """
        LOG.debug('set_output called with: %s', on_off)
        self.com('OUT' + ('1' if on_off else '0'))

    # Spec command 9
    def status(self):
        """Return the status

        The output is a dict with the following keys and types::

         status = {
             'channel1_mode': 'CV',  # or 'CC' for constand current of voltage
             'channel2_mode': 'CV',  # or 'CC' for constand current of voltage
             'beep_on': True,
             'lock_on': False,
             'output_on': True,
             'tracking_status: 'Independent',  # or 'Series' or 'Parallel'
         }

        Returns:
            dict: See fields specification above
        """
        LOG.debug('status called')
        status_byte = ord(self.com('STATUS?', decode_reply=False))
        # Convert to binary representation, zeropad and reverse
        status_bitstring = '{:0>8b}'.format(status_byte)[::-1]

        # Form a status dict
        status = {
            'channel1_mode': 'CV' if status_bitstring[0] == '1' else 'CC',
            'channel2_mode': 'CV' if status_bitstring[1] == '1' else 'CC',
            'beep_on': status_bitstring[4] == '1',
            'lock_on': status_bitstring[5] == '1',
            'output_on': status_bitstring[6] == '1',
        }
        tracking_bits = status_bitstring[2: 4]
        tracking_translation = {'00': 'Independent', '01': 'Series', '11': 'Parallel'}
        status['tracking_status'] = tracking_translation[tracking_bits]
        return status

    # Spec command 10
    def get_identification(self):
        """Return the device identification

        Returns:
            str: E.g: 'TENMA 72-2535 V2.0'
        """
        LOG.debug('get_identification called')
        return self.com('*IDN?')

    # Spec command 11
    def recall_memory(self, memory_number):
        """Recall memory of panel settings

        .. note:: Recalling memory will automaticall disable output

        Args:
            number (int): The number of the panel settings memory to recall

        Raises:
            ValueError: On invalid memory_number
        """
        LOG.debug('recall_memory called with: %s', memory_number)
        if memory_number not in range(1, 6):
            msg = 'Memory number must be int in range: {}'
            raise ValueError(msg.format(list(range(1, 6))))
        self.com('RCL{}'.format(memory_number))

    # Spec command 12
    def save_memory(self, memory_number):
        """Recall memory of panel settings

        .. note:: Saving to a memory slot seems to only be available for the memory slot
           currently active

        Args:
            number (int): The number of the panel settings memory to recall

        Raises:
            ValueError: On invalid memory_number

        """
        LOG.debug('save_memory called with: %s', memory_number)
        if memory_number not in range(1, 6):
            msg = 'Memory number must be int in range: {}'
            raise ValueError(msg.format(list(range(1, 6))))
        self.com('SAV{}'.format(memory_number))

    # Spec command 13
    def set_overcurrent_protection(self, on_off):
        """Set the over current protection (OCP) on or off

        Args:
            on_off (bool): The overcurrent protection mode to set
        """
        LOG.debug('set_overcurrent_protection called with: %s', on_off)
        self.com('OCP' + ('1' if on_off else '0'))

    # Spec command 14
    def set_overvoltage_protection(self, on_off):
        """Set the over voltage protection (OVP) on or off



        Args:
            on_off (bool): The overvoltage protection mode to set
        """
        LOG.debug('set_overvoltage_protection called with: %s', on_off)
        self.com('OVP' + ('1' if on_off else '0'))


class Tenma722535(TenmaBase):
    """Driver for the Tenma 72-2535 power supply"""


class Tenma722550(TenmaBase):
    """Driver for the Tenma 72-2550 power supply"""


class Tenma722930(TenmaBase):
    """Driver for the Tenma 72-2930 power supply"""


def main():
    """Main module function, used for testing simple functional test"""
    logging.basicConfig(level=logging.INFO)
    from random import random

    device = '/dev/serial/by-id/usb-USB_Vir_USB_Virtual_COM_NT2009101400-if00'
    tenma = Tenma722535(device)
    print('ID:', tenma.get_identification())
    print('Status:', tenma.status())

    current = random()
    print('\nSet current to:', current)
    tenma.set_current(current)
    print('Read current', tenma.get_current())

    voltage = random()
    print('\nSet voltage to:', voltage)
    tenma.set_voltage(voltage)
    print('Read voltage', tenma.get_voltage())

    tenma.set_output(True)
    print('\nActual current:', tenma.get_actual_current())
    print('Actual voltage:', tenma.get_actual_voltage())

    print('\nOvercurrent and overvoltage protection, watch the LEDS switch')
    tenma.set_overcurrent_protection(True)
    sleep(0.5)
    tenma.set_overcurrent_protection(False)
    sleep(0.5)
    tenma.set_overvoltage_protection(True)
    sleep(0.5)
    tenma.set_overvoltage_protection(False)

    print('\nSpeed test')
    t0 = time()
    for _ in range(10):
        value = tenma.get_voltage()
        now = time()
        print('Voltage:', value, 'read speed', now - t0, end=' ')
        t0 = now


if __name__ == '__main__':
    main()
