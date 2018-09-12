#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=too-many-instance-attributes,too-many-arguments

"""Drivers for the 4d systems displays

For usage examples see the file
PyExpLabSys/test/integration_tests/test_four_d_systems.py

.. note:: Only a small sub-set of the specification is plemented, but with the
    available examples it should be real easy to add more commands.

.. note:: An internal method '_to_16_bit_rgb' exists to convert a HTML hex
    color code or an RGB tuple of floats to the irregular 16 bit RGB color
    scale this device use. It should make working with colors a lot easier.

.. note:: The displays must be activated for serial communication. At present
    the only way we know how to do that, is to follow the procedure described
    in the serial specification, which involves taking it past a Windows
    program.

.. note:: At present only communication via the USB connection has been tested.
    For communication directly via the internal connection on the Raspberry Pi
    it may be necessary to do some preparation in order to free the pins up for
    serial communication.

.. seealso:: Docs for this implementation are on the wiki at:
    https://cinfwiki.fysik.dtu.dk/cinfwiki/Equipment#Picaso_uLCD-28PTU    or online at:
    http://www.4dsystems.com.au/product/4D_Workshop_4_IDE/downloads

"""

from __future__ import division, print_function, unicode_literals
# Forces imports of backports of python 3 functionality into python 2.7 with the
# python-future module
from builtins import (  # pylint: disable=redefined-builtin, unused-import
    bytes, dict, int, list, object, range, str, ascii, chr, hex, input, next, oct, open,
    pow, round, super, filter, map, zip
)

from time import sleep
from struct import pack
from functools import partial
import serial

try:
    from PIL import Image
except ImportError:
    Image = None

from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

# TODO: Implement proper logging

# Constant(s)
ACKNOWLEDGE = b'\x06'
TEXT_PROPERTY_TO_COMMAND = {
    'bold': b'\xFF\xDE',
    'inverse': b'\xFF\xDC',
    'italic': b'\xFF\xDD',
    'opacity': b'\xFF\xDF',
    'underline': b'\xFF\xDB'
}
SCREEN_MODES = ['landscape', 'landscape reverse', 'portrait', 'portrait reverse']
GRAPHICS_PARAMETERS = [
    'x_max', 'y_max', 'last_object_left', 'last_object_top', 'last_object_right',
    'last_object_bottom',
]
TOUCH_STATES = ['enable', 'disable', 'default']
TOUCH_STATUSSES = ['invalid/notouch', 'press', 'release', 'moving']
LATIN_DICT = {
    u"¡": u"!", u"¢": u"c", u"£": u"L", u"¤": u"o", u"¥": u"Y",
    u"¦": u"|", u"§": u"S", u"¨": u"`", u"©": u"c", u"ª": u"a",
    u"«": u"<<", u"¬": u"-", u"­": u"-", u"®": u"R", u"¯": u"-",
    u"°": u"o", u"±": u"+-", u"²": u"2", u"³": u"3", u"´": u"'",
    u"µ": u"u", u"¶": u"P", u"·": u".", u"¸": u",", u"¹": u"1",
    u"º": u"o", u"»": u">>", u"¼": u"1/4", u"½": u"1/2", u"¾": u"3/4",
    u"¿": u"?", u"À": u"A", u"Á": u"A", u"Â": u"A", u"Ã": u"A",
    u"Ä": u"A", u"Å": u"Aa", u"Æ": u"Ae", u"Ç": u"C", u"È": u"E",
    u"É": u"E", u"Ê": u"E", u"Ë": u"E", u"Ì": u"I", u"Í": u"I",
    u"Î": u"I", u"Ï": u"I", u"Ð": u"D", u"Ñ": u"N", u"Ò": u"O",
    u"Ó": u"O", u"Ô": u"O", u"Õ": u"O", u"Ö": u"O", u"×": u"*",
    u"Ø": u"Oe", u"Ù": u"U", u"Ú": u"U", u"Û": u"U", u"Ü": u"U",
    u"Ý": u"Y", u"Þ": u"p", u"ß": u"b", u"à": u"a", u"á": u"a",
    u"â": u"a", u"ã": u"a", u"ä": u"a", u"å": u"aa", u"æ": u"ae",
    u"ç": u"c", u"è": u"e", u"é": u"e", u"ê": u"e", u"ë": u"e",
    u"ì": u"i", u"í": u"i", u"î": u"i", u"ï": u"i", u"ð": u"d",
    u"ñ": u"n", u"ò": u"o", u"ó": u"o", u"ô": u"o", u"õ": u"o",
    u"ö": u"o", u"÷": u"/", u"ø": u"oe", u"ù": u"u", u"ú": u"u",
    u"û": u"u", u"ü": u"u", u"ý": u"y", u"þ": u"p", u"ÿ": u"y",
    u"’": u"'", u"č": u"c", u"ž": u"z"
}
BAUD_RATES = {
    110: 0,
    300: 1,
    600: 2,
    1200: 3,
    2400: 4,
    4800: 5,
    9600: 6,
    14400: 7,
    19200: 8,
    31250: 9,
    38400: 10,
    56000: 11,
    57600: 12,
    115200: 13,
    128000: 14,
    256000: 15,
    300000: 16,
    375000: 17,
    500000: 18,
    600000: 19,
}


def to_ascii(string):
    """Convert non-ascii character in a unicode string to ascii"""
    for char in string:
        if char in LATIN_DICT:
            string = string.replace(char, LATIN_DICT[char])
    return string


def to_ascii_utf8(string):
    """Convert non-ascii character in a utf-8 encoded string to ascii"""
    string = string.decode('utf-8')
    for char in string:
        if char in LATIN_DICT:
            string = string.replace(char, LATIN_DICT[char])
    return string.encode('utf-8')


# Create to_word function as a partial
to_word = partial(pack, '>H')  # pylint: disable=invalid-name


def to_words(*args):
    """Convert integers or tuples of integers to 2 byte words

    This will convert e.g args:
        1, 200 -> b'\x00\x01\x00\xc8'
        (1, 200) -> b'\x00\x01\x00\xc8'

    Args:
        args: integers or tuple of lists of integers

    Returns:
        bytes: The corresponding bytes string
    """
    convert = []
    for arg in args:
        if isinstance(arg, list):
            convert += arg
        elif isinstance(arg, tuple):
            convert += list(arg)
        else:
            convert.append(arg)
    return pack('>' + 'H' * len(convert), *convert)


def to_gci(image, resize=None):
    """Convert an imame to PICASO GCI format bytestring

    Args:
        image (str or PIL.Image): Path of image or PIL.Image object
        resize (tuple): A 2 element tuple (x, y) for resizing
    """
    if Image is None:
        message = 'The to_gci function requires PIL to be installed'
        raise RuntimeError(message)

    if not isinstance(image, Image.Image):
        image = Image.open(image)  # Can be many different formats.

    # Resize if requested
    if resize:
        image.resize(resize, Image.ANTIALIAS)

    # Get pixels and convert
    pixels = image.getdata()
    x, y = image.size
    # Get pixels as 1 byte color components (0-255), convert to 0.0-1.0 float color
    # components and finally convert to Picaso's 16 bit color format
    colors = [PicasoCommon._to_16_bit_rgb([x/255 for x in p]) for p in pixels]
    # NOTE: There is an error in the spec I found online:
    # https://forum.4dsystems.com.au/forum/forum-aa/faq-frequently-asked-questions/faq/
    # 2290-graphics-composer-and-the-display-modules
    # The color code is just one byte, followed by a zero byte
    data = to_words(x, y) + b'\x10\x00' + to_words(colors)

    # Pad data with zero bytes up to 512 bytes
    remainder = 512 - len(data) % 512
    data = data + b'\x00' * remainder
    return data


# pylint: disable=too-many-public-methods
class PicasoCommon(object):
    """Implementation of the common parts of the serial communication to the
    Picaso devices

    :raises: :py:class:`serial.serialutil.SerialException` - All public methods
        in this class may raise this exception if there are problems with the
        serial communication
    """

    def __init__(self, serial_device='/dev/ttyUSB0', baudrate=9600,
                 debug=False):
        """Initialize the driver

        The serial device and the baudrate are configurable, as described
        below. The rest of the serial communication parameters are; bytesize: 8
        bits, parity: None, stopbits: one (as per the manual) and a timeout of
        3 seconds.

        Args:
            serial_device (str): The serial device to open communication on
            baud_rate (int): The baudrate for the communication. This should be the baud
                rate the display is set for per default. The baud can be changed after
                instantiation with the :meth:`set_baud_rate` method
            debug (bool): Enable a check of whether there are bytes left in
                waiting after a reply has been fetched.
        """
        self.serial = serial.Serial(
            port=serial_device,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=3,
        )
        # Flush buffer
        number_of_old_bytes = self.serial.inWaiting()
        self.debug = debug

    def close(self):
        """Close the serial communication"""
        self.serial.close()

    def _send_command(self, command, reply_length=0, output_as_bytes=False,
                      reply_is_string=False):
        """Send a command and return status and reply

        Args:
            command (bytes): The command to send e.g. b'\xFF\xCD' to clear the screen
            reply_length (int): The length of the expected reply i.e. WITHOUT an
                acknowledge.
            output_as_bytes (bool): Return bytes instead of int
            reply_is_string (bool): Overrides the `reply_length` and read the reply
                length from the reply itself. Applicaple only to variable length strings.

        Returns:
            bytes or int: If a return value is requested (with reply_length) a int will be
            returned formed from the bytes. If output_as_bytes is set, then the raw bytes
            are returned

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the requested length
        """
        if self.debug:
            print("Repr of command to send", repr(command))
        self.serial.write(command)

        # Special case for baud rate change
        command_as_bytes = bytes(command)
        if command_as_bytes[0: 2] == b'\x00\x26':
            baudrate_index = int.from_bytes(command_as_bytes[2:], byteorder='big')
            baudrate = {v: k for k, v in BAUD_RATES.items()}[baudrate_index]
            sleep(1)
            self.serial.baudrate = baudrate
            while True:
                if self.serial.inWaiting() > 0:
                    ack = self.serial.read(1)
                    # For some reason, it doesn't seem to return ACK, but it has done it,
                    # which is why we return after getting a byte back
                    break
                sleep(0.1)
            return

        # First check if it succeded
        acknowledge_as_byte = self.serial.read(1)
        if acknowledge_as_byte != b'\x06':
            message = 'The command \'{}\' failed with code: {}'.format(command,
                                                                       acknowledge_as_byte)
            raise PicasoException(message, exception_type='failed')

        # The read reply is any
        if reply_is_string:
            reply_length = 0
            string_length_as_bytes = self.serial.read(2)
            string_length = int.from_bytes(string_length_as_bytes, byteorder='big')
            reply_raw = self.serial.read(string_length)
        else:
            if reply_length > 0:
                reply_raw = self.serial.read(reply_length)
            else:
                reply_raw = b''

        # Make sure there is nothing waiting
        if self.debug:
            in_waiting = self.serial.inWaiting()
            if in_waiting != 0:
                message = 'Wrong reply length. There are still {0} bytes '\
                          'left waiting on the serial port'.format(in_waiting)
                raise PicasoException(message, exception_type='bytes_still_waiting')

        # Return appropriate value
        if reply_length > 0:
            if len(reply_raw) != reply_length:
                message = 'The reply length {0} bytes, did not match the '\
                          'requested reply length {1} bytes'.format(
                              len(reply_raw) - 1, reply_length)
                raise PicasoException(message, exception_type='unexpected_reply')

        reply = None
        if output_as_bytes or reply_is_string:
            reply = reply_raw
        else:
            reply = int.from_bytes(reply_raw, byteorder='big')
        return reply

    @staticmethod
    def _to_16_bit_rgb(color):
        """Convert a color to the `non regular 16 bit RGB
        <http://en.wikipedia.org/wiki/List_of_monochrome_and_RGB_palettes
        #16-bit_RGB>`_.

        Args:
            color (str or tuple): 24 bit RGB HTML hex string e.g. ``'#ffffff'``
            or RGB tuple or floats e.g. ``(1.0, 1.0, 1.0)``

        Returns:
            str: An integer that represents the 2 bytes
        """
        # 5 bits for red and blue and 6 for green
        if isinstance(color, str):
            # Convert e.g. '#ffffff' to [1.0, 1.0, 1.0]
            color = [int(color[n: n+2], base=16) / 255 for n in range(1, 6, 2)]

        # '0001100011001001'
        #  |-r-||--g-||-b-|
        bitstring = '{:05b}{:06b}{:05b}'.format(int(color[0] * 31),
                                                int(color[1] * 63),
                                                int(color[2] * 31))
        # Turn the bit string into an integer and return
        return int(bitstring, 2)

    @staticmethod
    def _from_16_bit_rgb(color):
        """Convert a `non regular 16 bit RGB
        <http://en.wikipedia.org/wiki/List_of_monochrome_and_RGB_palettes
        #16-bit_RGB>`_ to tuple of float e.g (1.0, 0.0, 1.0)

        Args:
            color (int): Integer representing the two bytes that form the color

        Returns:
            tuple: Color as tuple of floats e.g. (1.0, 0.0, 1.0)
        """
        # '0001100011001001'
        #  |-r-||--g-||-b-|
        bitstring = '{:0>16b}'.format(color)
        out = []
        # Extract the r, g and b parts from the bitstring
        for start, end in ((0, 5), (5, 11), (11, 16)):
            # Convert to absolute int value
            as_int = int(bitstring[start: end], 2)
            # Convert to relative float (0.0 - 1.0)
            as_float = as_int / (2 ** (end - start) - 1)
            out.append(as_float)
        return tuple(out)

    # TEXT AND STRING COMMANDS, section 5.1 in the manual
    def move_cursor(self, line, column):  # Section .1
        """Move the cursor to line, column

        The actual position in which the cursor is placed is based on the
        current text parameters such as width and height

        Args:
            line (int): The line number to move the cursor to
            column (int): The column to move the cursor to

        Raises:
            PicasoException: If the command fails
        """
        command = b'\xFF\xE9' + to_words(line, column)
        self._send_command(command)

    def put_string(self, string):  # Section .3
        """Write a string on the display

        .. note:: It has not been investigated whether characters outside of
            ASCII can be used. If that becomes necessary, try, and possibly
            consult the manual

        Args:
            string (str): Ascii string to write, max length 511 chars

        Returns:
            int: The number of bytes written

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        command = b'\x00\x18' + string.encode('ascii') + b'\x00'
        return self._send_command(command, 2)

    def character_width(self, character):  # Sub-section .4
        """Get the width of a character in pixels with the current font

        Args:
            character (str): Character to get the width of

        Returns:
            int: The width in pixels

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        :raises: :py:class:`~exceptions.ValueError` - If ``character`` does not
            have length 1
        """

        if len(character) != 1:
            raise ValueError('Character must be a string of length 1')
        command = b'\x00\x1E' + character.encode('ascii')
        return self._send_command(command, 2)

    def character_height(self, character):  # Sub-section .5
        """Get the height of a character in pixels with the current font

        Args:
            character (str): Character to get the height of

        Returns:
            int: The height in pixels

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        :raises: :py:class:`~exceptions.ValueError` - If ``character`` does not
            have length 1
        """
        if len(character) != 1:
            raise ValueError('character must be a string of length 1')
        command = b'\x00\x1D' + character.encode('ascii')
        return self._send_command(command, 2)

    def text_foreground_color(self, color):  # Sub-section .6
        """Sets the foreground color of the text

        Args:
            color (tuple or string): 24 bit RGB HTML hex string e.g. '#ffffff'
                or RGB tuple or floats e.g. (1.0, 1.0, 1.0)

        Returns:
            tuple: Previous color as tuple of floats e.g. (1.0, 1.0, 1.0)

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        command = b'\xFF\xE7' + to_word(self._to_16_bit_rgb(color))
        return self._from_16_bit_rgb(self._send_command(command, 2))

    def text_background_color(self, color):  # Sub-section .7
        """Sets the background color of the text

        Args:
            color (tuple or string): 24 bit RGB HTML hex string e.g. '#ffffff'
                or RGB tuple or floats e.g. (1.0, 1.0, 1.0)

        Returns:
            tuple: Previous color as tuple of floats e.g. (1.0, 1.0, 1.0)

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        command = b'\xFF\xE6' + to_word(self._to_16_bit_rgb(color))
        return self._from_16_bit_rgb(self._send_command(command, 2))

    def text_width(self, factor):  # Sub-section .9
        """Sets the text width

        Args:
            factor (int): Width multiplier (1-16) relative to default width

        Returns:
            int: Previous width multiplier

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        command = b'\xFF\xE4' + to_word(factor)
        return self._send_command(command, 2)

    def text_height(self, factor):  # Sub-section .10
        """Sets the text height

        Args:
            factor (int): Height multiplier (1-16) relative to default height

        Returns:
            int: Previous height multiplier

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        command = b'\xFF\xE3' + to_word(factor)
        return self._send_command(command, 2)

    def text_factor(self, factor):  # Sub-section .9 and .10
        """Sets the text width and height

        Args:
            factor (int): Width and height multiplier (1-16) relative to
                default width and height

        Returns:
            tuple: Previous width and height multipliers

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        previous_width = self.text_width(factor)
        previous_height = self.text_height(factor)
        return previous_width, previous_height

    def text_x_gap(self, pixels):  # Sub-section .11
        """Sets the horizontal gap between chars in pixels

        Args:
            pixels (int): The requested horizontal gap in pixels

        Return:
            int: The previous horizontal gap in pixels

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        command = b'\xFF\xE2' + to_word(pixels)
        return self._send_command(command, 2)

    def text_y_gap(self, pixels):  # Sub-section .11
        """Sets the vertical gap between chars in pixels

        Args:
            pixels (int): The requested vertical gap in pixels

        Return:
            int: The previous vertical gap in pixels

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        command = b'\xFF\xE1' + to_word(pixels)
        return self._send_command(command, 2)

    def text_attribute(self, attribute, status=True):  # Sub-section .13 - .17
        """Sets the text attribute status

        Args:
            attribute (str): The attribute to set, can be one of 'bold',
                'inverse', 'italic', 'opacity' and 'underline' where 'inverse'
                inter changes the back and foreground colors of the text
            status (bool): Boolean for the text attribute status, where True
                means 'on' or 'opaque' in the case of opacity

        Returns:
            bool: The previous status

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        :raises: :py:class:`~exceptions.ValueError` - If ``attribute`` is
            unknown
        """
        if attribute not in TEXT_PROPERTY_TO_COMMAND:
            message = 'Attribute \'{0}\' unknown. Valid attributes are {1}'\
                .format(attribute, TEXT_PROPERTY_TO_COMMAND.keys())
            raise ValueError(message)
        status = b'\x00\x01' if status else b'\x00\x00'
        command = TEXT_PROPERTY_TO_COMMAND[attribute] + status
        reply = self._send_command(command, 2)
        return True if reply == 1 else False

    # GRAPHICS COMMANDS, section 5.2 in the manual
    def clear_screen(self):  # Sub-section .1
        """Clear the screen

        Raises:
            PicasoException: If the command fails
        """
        self._send_command(b'\xFF\xCD')

    def draw_line(self, start, end, color):  # Sub-section .5
        """Draw a line from x1, y1 to x2, y2 and return boolean for success

        Args:
            start (tuple): Start point (x, y), where x and y are ints
            end (tuple): End point (x, y), where x and y are ints
            color (tuple or string): 24 bit RGB HTML hex string e.g. '#ffffff'
                or RGB tuple or floats e.g. (1.0, 1.0, 1.0)

        Raises:
            PicasoException: If the command fails
        """
        command = b'\xFF\xC8' + to_words(start, end, self._to_16_bit_rgb(color))
        self._send_command(command)

    def draw_rectangle(self, top_left, bottom_right, color):  # Sub-section .6
        """Draw a rectangle

        Args:
            top_left (tuple): Coordinates of top left corner (x, y)
            bottom_right (tuple): Coordinates of bottom right corner (x, y)
            color (tuple or string): 24 bit RGB HTML hex string e.g. '#ffffff'
                or RGB tuple or floats e.g. (1.0, 1.0, 1.0)

        Raises:
            PicasoException: If the command fails
        """
        command = b'\xFF\xC5' + to_words(top_left, bottom_right, self._to_16_bit_rgb(color))
        self._send_command(command)

    # Sub-section .6
    def draw_filled_rectangle(self, top_left, bottom_right, color):
        """Draw a filled rectangle

        Args:
            top_left (tuple): Coordinates of top left corner (x, y)
            bottom_right (tuple): Coordinates of bottom right corner (x, y)
            color (tuple or string): 24 bit RGB HTML hex string e.g. '#ffffff'
                or RGB tuple or floats e.g. (1.0, 1.0, 1.0)

        Raises:
            PicasoException: If the command fails
        """
        command = b'\xFF\xC4' + to_words(top_left, bottom_right, self._to_16_bit_rgb(color))
        self._send_command(command)

    # Sub-section .14
    def put_pixel(self, x, y, color):
        """Set a pixel
        """
        command = b'\xFF\xC1' + to_words(x, y, self._to_16_bit_rgb(color))
        self._send_command(command)

    def move_origin(self, x, y):
        """Move the origin to a point, forming the basis for the next graphics
        or text command

        Args:
            x (int): X-coordinate for the new origin
            y (int): Y-coordinate for the new origin

        Raises:
            PicasoException: If the command fails
        """
        command = b'\xFF\xCC' + to_words(x, y)
        self._send_command(command)

    def screen_mode(self, mode):  # Sub-section 34
        """Sets the screen mode

        Args:
            mode (str): The mode for the screen. Can be either ``'landscape'``,
                ``'landscape reverse'``, ``'portrait'`` or
                ``'portrait reverse'``

        Returns:
            str: Returns previous screen mode on success or ``None`` on failure

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        command = b'\xFF\x9E' + to_word(SCREEN_MODES.index(mode))
        layout_number = self._send_command(command, 2)
        return SCREEN_MODES[layout_number]

    def get_graphics_parameters(self, parameter):  # Sub-section 38
        """Gets graphics parameters

        .. note:: The meaning of the results from the ``'last_object_*'``
            parameters is not known. It was expected to be coordinates, but
            they are much to large

        Args:
            parameter (str): The parameter to fetch, can be ``'x_max'`` for
            the x resolution under the current orientation, ``'y_max'`` for
            the y resolution under the current orientation,
            ``'last_object_left'``, ``'last_object_top'``,
            ``'last_object_right'``, ``'last_object_bottom'`` for the relevant
            parameter for the last object.

        Returns:
          int: The requested parameter

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        command = b'\xFF\xA6' + to_word(GRAPHICS_PARAMETERS.index(parameter))
        return self._send_command(command, 2)

    # MEDIE COMMANDS, section 5.3 in the manual
    def media_init(self):  # Sub-section .1
        """Initialize a uSD/SD/SDHC memory card for media operations

        Returns:
            bool: True is the memory card was present and successfully initialized and
            False otherwise
        """
        return_value = self._send_command(b'\xFF\x89', 2)
        return return_value == 1

    def set_sector_address(self, high_word, low_word):
        """Set the internal adress pointer for a sector

        The two argumenst are the two upper and lower bytes of a 4 byte sector address
        respectively. I.e. the total sector address will be formed as: `high_word * 65535
        + low_word`

        Args:
            high_word (int): An integer between 0 and 65535. See above.
            low_word (int): An integer between 0 and 65535. See above.
        """
        self._send_command(b'\xFF\x92' + to_words(high_word, low_word))

    def read_sector(self):
        """Read the block (512 bytes) at the sector address pointer

        Raises:
            PicasoException: If the sector read fails

        The address pointer is set with :meth:`set_sector_address`. After the read, the
        sector address pointer will be incremented by 1.

        """
        val = self._send_command(b'\x00\x16', reply_length=514, output_as_bytes=True)
        success = to_word(val[:2])
        if success != 1:
            message = 'Sector read failed'
            raise PicasoException(message, exception_type='sector_read_failed')
        return val[2:]

    def write_sector(self, block):
        """Write a block (512 bytes) to the sector at the sector address pointer

        .. note:: The size of block must be 512 bytes

        .. note:: Rememer to call :meth:`flush` after writes to ensure that they are
           written out to the SD-card

        Returns:
            bool: Write successful

        The address pointer is set with :meth:`set_sector_address`. After the write, the
        sector address pointer will be incremented by 1.
        """
        return_value = self._send_command(b'\x00\x17' + block, 2)
        return return_value == 1

    def write_sectors(self, blocks):
        """Write multiple blocks to consequtive sectors starting at the sector adddress pointer

        This is a convenience method around several calls to :meth:`write_sector`.

        .. note:: The size of blocks must be a multiple of 512 bytes

        .. note:: Rememer to call :meth:`flush` after writes to ensure that they are
           written out to the SD-card

        Args:
            blocks (bytes): The data to write

        Returns:
            bool: Whether all writes were successful

        """
        successes = []
        for position in range(0, len(blocks), 512):
            block = blocks[position: position + 512]
            successes.append(self.write_sector(block))
        return all(successes)

    def flush_media(self):
        """Ensure that data written is actually written out to the SD card

        Returns:
            bool: Whether flush operation was successful
        """
        val = self._send_command(b'\xFF\x8A', 2)
        return val != 0

    def display_image(self, x, y):
        """Display the image at the sector pointer or byte pointer at x, y coordinates

        Args:
            x (int): X-coordinate of the upper left corner
            y (int): Y-coordinate of the upper left corner
        """
        self._send_command(b'\xFF\x8B' + to_words(x, y))

    # SERIAL UART COMMUNICATIONS COMMANDS, section 5.4 in the manual
    def set_baud_rate(self, baud_rate):
        """Set the communication baud rate

        .. note:: This change will affect only the current session

        Args:
            baud_rate (int): The baud rate to set. Valid values are keys in BAUD_RATES
        """
        try:
            index = BAUD_RATES[baud_rate]
        except KeyError:
            message = "Invalid baud rate {} requested. Valid values are: {}"
            raise ValueError(message.format(baud_rate, list(BAUD_RATES.keys())))
        self._send_command(b'\x00\x26' + to_word(index))

    # TOUCH SCREEN COMMANDS, section 5.8 in the manual
    def touch_detect_region(self, upper_left, bottom_right):  # Sub-section .1
        """Specify a touch detection region

        Args:
            upper_left (tuple): ``(x, y)`` for the upper left corner, where x
                and y are ints
            bottom_right (tuple): ``(x, y)`` for the lower right corner, where
                x and y are ints

        Raises:
            PicasoException: If the command fails
        """
        command = b'\xFF\x39' + to_words(upper_left, bottom_right)
        self._send_command(command)

    def touch_set(self, mode):  # Sub-section .2
        """Set touch screen related parameters

        Args:
            mode (string): The mode to set. It can be either ``'enable'``;
            which enables and initializes the touch screen, ``'disable'``
            which disables the touch screen or ``'default'`` which will reset
            the current active region to the default which is the full screen
            area.

        Raises:
            PicasoException: If the command fails
        """
        mode = TOUCH_STATES.index(mode)
        command = b'\xFF\x38' + to_word(mode)
        self._send_command(command)

    def touch_get_status(self):  # Sub-section .3
        """Return the state of the touch screen

        Returns:
            str: The state of the touch screen, can be either
            ``'invalid/notouch'``, ``'press'``, ``'release'``, ``'moving'`` or
            ``None`` on error

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        touch_status_number = self._send_command(b'\xFF\x37\x00\x00', 2)
        return TOUCH_STATUSSES[touch_status_number]

    def touch_get_coordinates(self):  # Sub-section .3
        """Return the coordinates of the LAST touch event

        Returns:
            tuple: ``(x, y)`` where x and y are ints

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        x_coord = self._send_command(b'\xFF\x37\x00\x01', 2)
        y_coord = self._send_command(b'\xFF\x37\x00\x02', 2)
        return x_coord, y_coord

    # SYSTEM COMMANDS, section 5.10 in the manual
    def get_display_model(self):  # Sub-section .3
        """Get the display model

        Returns:
            str: The display model

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        reply = self._send_command(b'\x00\x1A', reply_is_string=True)
        return reply.decode('ascii')

    def get_spe_version(self):  # Sub-section .4
        """Get the version of the Serial Platform Environment

        Returns:
            str: The version or ``None`` on failure

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        reply = self._send_command(b'\x00\x1B', 2, output_as_bytes=True)
        return '{}.{}'.format(*bytearray(reply))


class PicasouLCD28PTU(PicasoCommon):
    """Driver for the Picaso 28 PTU Pi LCD display

    For details on the methods that can be called on this class see the
    documentation for :py:class:`PicasoCommon`
    """

    def __init__(self, serial_device='/dev/ttyUSB0', baudrate=9600,
                 debug=False):
        super(PicasouLCD28PTU, self).__init__(serial_device, baudrate)


class PicasoException(Exception):
    """Exception for Picaso communication

    The ``exception_type`` parameter can be either, ``'failed'`` or
    ``'unexpected_reply'``
    """

    def __init__(self, message, exception_type):
        super(PicasoException, self).__init__(message)
        self.exception_type = exception_type


class Button(object):
    """Class that represents a button to use in the interface"""

    def __init__(self, picaso, top_left, bottom_right, text,
                 text_justify='center', left_justify_indent=None,
                 text_color='#000000', inactive_color='#B2B2B2',
                 active_color='#979797'):
        self.picaso = picaso
        self.text = text
        self.text_justify = text_justify
        self.left_justify_indent = left_justify_indent
        self.text_color = text_color
        self.inactive_color = inactive_color
        self.active_color = active_color
        # Geometry
        self.top_left = None
        self.bottom_right = None
        self.button_height = None
        self.button_width = None
        self.set_position(top_left, bottom_right)
        # Text properties
        self.char_height = picaso.character_height('C')
        self.char_width = picaso.character_width('C')

    def set_position(self, top_left, bottom_right):
        """Set position of the button"""
        self.top_left = top_left
        self.bottom_right = bottom_right
        self.button_height = bottom_right[1] - top_left[1]
        self.button_width = bottom_right[0] - top_left[0]

    def draw_button(self, active=False):
        """Draw button with either its active or inactive background color"""
        # Draw rectangle
        color = self.active_color if active else self.inactive_color
        self.picaso.draw_filled_rectangle(self.top_left, self.bottom_right,
                                          color)

        # Calculate text origin y-coordinate by creating splitting remaining
        # vertical space or default to top of button
        origin_y = (self.button_height - self.char_height) // 2 +\
                   self.top_left[1]
        origin_y = max(origin_y, self.top_left[1])

        # Calculate text origin x-coordinate dependent on justification
        if self.text_justify == 'left':
            # If left
            if self.left_justify_indent:
                origin_x = self.top_left[0] + self.left_justify_indent
            else:
                origin_x = self.top_left[0] + self.char_width // 2
        else:
            text_width = len(self.text) * self.char_width
            origin_x = (self.button_width - text_width) // 2 + self.top_left[0]
            origin_x = max(origin_x, self.top_left[0])

        # Set text background and foreground color and write text
        self.picaso.move_origin(origin_x, origin_y)
        old_foreground_color = self.picaso.text_foreground_color(
            self.text_color)
        old_background_color = self.picaso.text_background_color(color)
        self.picaso.put_string(self.text)
        # Restore colors
        self.picaso.text_foreground_color(old_foreground_color)
        self.picaso.text_background_color(old_background_color)
