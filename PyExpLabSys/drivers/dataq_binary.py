# pylint: disable=no-member

"""DataQ Binary protocol driver

To get started using the one of the supported DataQ data cards, use one of the
sub-classes of DataQBinary e.g. DI1110, set scan list and start:

.. code-block:: python

   # Instantiate dataq object
   dataq = DI1110('/dev/ttyUSB0')

   # Get all available information from the data cards
   print(repr(dataq.info()))

   # Set sample rate frequence
   dataq.sample_rate(1000)

   # Set scan list (meaure on channel 1 first, then 0 and finnaly 2)
   dataq.scan_list([1, 0, 2])

   dataq.clear_buffer()
   dataq.start()
   sleep(0.1)
   from pprint import pprint
   try:
       while True:
           pprint(dataq.read())
           sleep(0.5)
   except KeyboardInterrupt:
       dataq.stop()
   else:
       dataq.stop()
   dataq.clear_buffer()

If the data card is being used on the limit of emptying the data buffer before it
overflow, it might be useful to put the calls to ``read`` in a try except:

.. code-block:: python

   while True:
       try:
           dataq.read()
       except dataq_binary.BufferOverflow:
           # Re-start i.e. stop and start

or, to simple start and stop the card for a short amount of time, if slow measurements, which would otherwise fill buffer are required:

.. code-block:: python

   while True:
       dataq.start()
       sleep(0.1)
       dataq.read()
       dataq.stop()
       # We really only need to measure every 10s
       sleep(10)

On some Linux system, at the end of 2017, some models, e.g. the DI-1110 wasn't
automatically mounted. In that case, it can be manually mounted with a command
like this one:

.. code-block:: bash

   sudo modprobe usbserial vendor=0x0683 product=0x1110

On should be possible, on Debian based Linux systems to add an automatic mount
rule along the lines of this thread:
https://askubuntu.com/questions/525016/cant-open-port-dev-ttyusb0

So, add a new udev rule /etc/udev/rules.d/99-dataq_di1110.rules

with this content:

.. code-block:: text

   # /etc/udev/rules.d/99-dataq_di1110.rules
   # contains DataQ DI-1110 udev rule to patch default
   # rules
   SYSFS{idProduct}=="1110",
   SYSFS{idVendor}=="0683",
   RUN+="/sbin/modprobe -q usbserial product=0x1110 vendor=0x0683"

and aftwerwards run: sudo udevadm control --reload-rules

"""

from __future__ import print_function

from time import sleep
import logging

import serial
import numpy

from PyExpLabSys.common.supported_versions import python2_and_3
# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)


class BufferOverflow(Exception):
    """Custom exception to indicate a buffer overflow"""
    pass


class DataQBinary(object):
    """Base class for DataQBinary driver"""

    #: Serial communication end character
    end_char = '\r'
    #: Wait time between serial write and read
    read_wait_time = 0.001
    #: Information items that can be retrieved along with their code number
    infos = {
        'vendor': 0,
        'device name': 1,
        'firmware revision': 2,
        'serial number': 6,
        'sample rate divisor': 9,
    }
    #: Supported LED colors along with the code number
    led_colors = {
        'black': 0, 'blue': 1, 'green': 2, 'cyan': 3,
        'red': 4, 'magenta': 5, 'yellow': 6, 'white': 7,
    }
    #: Buffer overflow size, may be overwritte in sub classes
    buffer_overflow_size = 4095

    #: Packet sizes and code numbers
    packet_sizes = {
        16: 0,
        32: 1,
        64: 2,
        128: 3,
        256: 4,
        512: 5,
        1024: 6,
        2048: 7,
    }

    def __init__(self, device, serial_kwargs=None):
        """Initialize local variables

        Args:
            device (str): The device e.g: '/dev/ttyUSB0' of 'COM1'
            serial_kwargs (dict): dict of keyword arguments for serial.Serial
        """
        if serial_kwargs is None:
            serial_kwargs = {}
        self.serial = serial.Serial(device, **serial_kwargs)

        # Stop any active acquisition and clear buffer
        self.stop()
        self.clear_buffer()

        # Initialize variables
        self.expect_echo = True
        self._scan_list = [0]
        self._position_in_scanlist = 0
        self._sample_rate_divisor = int(self.info('sample rate divisor'))

    def clear_buffer(self):
        """Clear the buffer"""
        sleep(0.5)
        while self.serial.inWaiting() > 0:
            self.serial.read(self.serial.inWaiting())

    def _comm(self, arg, read_reply_policy='read'):
        """Execute command and return reply"""
        # Form command and send
        command = (arg + self.end_char)
        self.serial.write(command.encode())
        LOGGER.debug("cmd: %s", command)
        if read_reply_policy == 'dont_read':
            return ''

        # Read until reply end string
        return_string = ''
        while return_string == '' or not return_string.endswith(self.end_char):
            sleep(self.read_wait_time)
            bytes_waiting = self.serial.inWaiting()
            bytes_read = self.serial.read(bytes_waiting)
            # For the stop command, the reply might have a bit a data
            # prefixed, so just don't interpret the reply
            if read_reply_policy == 'dont_interpret':
                return ''
            return_string += bytes_read.decode().rstrip('\x00')
        LOGGER.debug("reply: %s", return_string)

        # Strip echo if present
        if self.expect_echo and return_string.startswith(arg):
            return_string = return_string.replace(arg + ' ', '', 1)

        # And finally end_char when we return the result
        return return_string.strip(self.end_char)


    def info(self, info_name='all'):
        """Return information about the device

        Args:
            info_name (str): Name of the requested information
                item(s). If info_name is one the specific info names,
                (the keys in DataQBinary.infos), a string will be
                returned with the value. If info_name is 'all', all
                values will be returned in a dict
        Returns:
            str or dict: Information items
        """
        if info_name == 'all':
            out = {}
            for name, number in self.infos.items():
                command = 'info {}'.format(number)
                out[name] = self._comm(command)
            return out

        if info_name not in self.infos:
            msg = 'Invalid info_name. Valid value are: {} and "all"'
            raise ValueError(msg.format(self.infos.keys()))
        command = 'info {}'.format(self.infos[info_name])
        return self._comm(command)

    def start(self):
        """Start data acquisition"""
        self.expect_echo = False
        self._comm('start 0', read_reply_policy='dont_read')

    def stop(self):
        """Stop data acquisition

        This also implies clearing the buffer of any remaining data
        """
        self.expect_echo = True
        self._comm('stop', read_reply_policy='dont_interpret')
        # This shouldn't be necessary
        self.clear_buffer()

    def scan_list(self, scan_list):
        """Set the scan list

        The scan list is the list of inputs to acquire from on the
        data card. The scan list can hold up to 11 items, since there
        are a total on 11 inputs and each element can only be there
        once. The analogue input channel are numbered 0-7, 8 is the
        counter channel, 9 is the rate channel and 10 is the general
        purpose input channel. 0.7 are specified only by their number,
        8, 9 and 10 are configured specially, which is not described
        here yet.

        Args:
            scan_list (list): Etc. [3, 5, 0] for analogue input chanel 3, 5
                and 0. NOTE: The numbers are integers, not strings.
        """
        LOGGER.debug("Set scan list: %s", scan_list)
        # Check for valid scan list configuratio
        for scan_list_configuration in scan_list:
            if scan_list_configuration not in range(8):
                msg = 'Only scan list arguments 0-7 are supported'
                raise ValueError(msg)
        # Check for duplicate entries
        if len(set(scan_list)) != len(scan_list):
            msg = 'The scan list is not allowed to have duplicate entries'
            raise ValueError(msg)

        # Send the configuration
        for slot_number, configuration in enumerate(scan_list):
            command = 'slist {} {}'.format(slot_number, configuration)
            self._comm(command)

        self._scan_list = scan_list

    def sample_rate(self, rate):
        """Set the sample rate

        The value values are calculated as being in the range of

          sample rate divisor / 375   to   sample rate divisor / 65535

        So e.g. for the DI-1110 product, with a sample rate divisor of
        60,000,000, the valid inputs are in range from 915.5413 to 160000.

        Args:
            rate (float): The sample rate given in number of elements in the scan
                list sampled per second (i.e. in Hz). Valid values depend on the
                model and is given by the "sample rate divisor" information item
                (see the info method). See information about how to calculate the
                valid input range above.

        """

        rate_for_command = int(self._sample_rate_divisor / float(rate))
        # Coerce in valid range
        rate_for_command = min(max(375, rate_for_command), 65535)
        self._comm('srate {}'.format(rate_for_command))

    def packet_size(self, size):
        """Set the packet size

        The packet size is he amount of data acquired before it is placed in the
        read buffer. The available packet sizes are the keys in packet_sizes
        class variable.

        Args:
            size (int): The requested packet size
        """
        if size not in self.packet_sizes:
            msg = 'Invalid packet size. Available values are: {}'
            raise ValueError(msg.format(self.packet_sizes.keys()))
        packet_size_number = self.packet_sizes[size]
        command = 'ps {}'.format(packet_size_number)
        self._comm(command)

    def led_color(self, color):
        """Set the LED color

        Args:
            color (str): The available colors are the keys in the led_colors
                class variable
        """
        if color not in self.led_colors:
            msg = 'Invalid color. Available colors are: {}'
            raise ValueError(msg.format(self.led_colors.keys()))
        color_number = self.led_colors[color]
        command = 'led {}'.format(color_number)
        self._comm(command)

    def read(self):
        """Read all values waiting

        This method reads all available damples from the data card and returns
        for every channel the mean of those samples.

        The returned data is on the form of a list with one item for each item
        in the scan list and in the same order. Each of the items is in them
        selves a dict, which holds the mean value of the samples, the number of
        samples in the mean, the channel number (0-based) and information about
        how full the data buffer was, at the time when it was read out. An
        example could be:

        .. code-block:: python

            [{'buffer_status': '3040/4095 bytes',
              'channel': 1,
              'samples': 506,
              'value': -1.6224543756175889},
             {'buffer_status': '3040/4095 bytes',
              'channel': 0,
              'samples': 507,
              'value': -0.0044494267751479287},
             {'buffer_status': '3040/4095 bytes',
              'channel': 2,
              'samples': 507,
              'value': 1.6192735299556213}]

        where the scan list was set to [1, 0, 2].

        Returns:
            list: A list of values for each of the items in the scan-list and
                in the same order. For details of returns values see above.

        Raises:
            BufferOverflow: If the buffer was full at the time of reading. The
                behavior in this case is ill-defined, so it is better to
                re-start the measurement if that happens.

        """
        # Form the output list and check for data
        n_input_channels = len(self._scan_list)
        list_out = [None] * n_input_channels
        waiting = self.serial.inWaiting()
        if waiting == 0:
            return list_out

        # Read and ...
        bytes_read = self.serial.read(waiting)
        # ... check for buffer overflow
        if len(bytes_read) == self.buffer_overflow_size:
            msg = ("Buffer flowed over. Adjust sampling parameters and restart "
                   "measurement.")
            raise BufferOverflow(msg)
        buffer_message = '{}/{} bytes'.format(
            len(bytes_read), self.buffer_overflow_size,
        )

        # Parse and interpret the data
        list_out = self._parse_data_packet(bytes_read, list_out)
        # Add buffer status
        for item in list_out:
            if item is not None:
                item['buffer_status'] = buffer_message
        return list_out

    def _parse_data_packet(self, bytes_read, list_out):
        """Parse a data packet"""
        n_input_channels = len(self._scan_list)
        # If any of the items in the scan list are analogue inputs,
        # calculate, parse the 2 byte words as int16 and convert to
        # float voltage values
        if any(n in range(0, 8) for n in self._scan_list):
            ints = numpy.frombuffer(bytes_read, dtype='int16')
            # NOTE on shift FIXME
            values = numpy.right_shift(ints, 4) * 10.0 / 2048

        # Start in the scan list at the saved position
        position_in_scanlist = self._position_in_scanlist

        # Loop over the offsets in the raw values, to calculate average
        for offset in range(n_input_channels):
            # Extract the actual channel number from the scan list
            channel = self._scan_list[position_in_scanlist]

            # If the input is a analogue input
            if channel in range(0, 8):
                # Extracts every n_input_channels items at offset
                values_this_channel = values[offset::n_input_channels]
                channel_out = {
                    'value': values_this_channel.mean(),
                    'samples': values_this_channel.size,
                    'channel': channel,
                }
                list_out[position_in_scanlist] = channel_out
            else:
                msg = "Only analogue input channel supported so far"
                raise RuntimeError(msg)

            position_in_scanlist = (position_in_scanlist + 1) % n_input_channels

        # Calculate scan list position to start from next time
        self._position_in_scanlist += (len(bytes_read)) // 2 % n_input_channels
        self._position_in_scanlist = self._position_in_scanlist % n_input_channels
        return list_out


class DI1110(DataQBinary):
    """FIXME"""
    buffer_overflow_size = 4095


def module_test():
    """Run primitive module tests"""
    logging.basicConfig(level=logging.DEBUG)
    global LOGGER  # pylint: disable=global-statement
    LOGGER = logging.getLogger('module_test')

    # Instantiate driver and print info
    dataq = DI1110('/dev/ttyUSB0')
    print(repr(dataq.info()))

    # Set sample rate
    dataq.sample_rate(1000)
    dataq.scan_list([1, 0, 2])

    dataq.led_color('red')
    # Start measurement
    #dataq.start()
    #sleep(0.1)
    from pprint import pprint
    try:
        while True:
            dataq.start()
            sleep(0.1)
            pprint(dataq.read())
            dataq.stop()
            sleep(3)
    except KeyboardInterrupt:
        dataq.stop()
    else:
        dataq.stop()
    dataq.clear_buffer()



if __name__ == '__main__':
    module_test()
