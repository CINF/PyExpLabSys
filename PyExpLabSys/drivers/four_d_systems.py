#!/usr/bin/env python
# pylint: disable=W0142

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


import serial

# Constant(s)
ACKNOWLEDGE = '\x06'
TEXT_PROPERTY_TO_COMMAND = {
    'bold': 'FFDE',
    'inverse': 'FFDC',
    'italic': 'FFDD',
    'opacity': 'FFDF',
    'underline': 'FFDB'
}
SCREEN_MODES = ['landscape', 'landscape reverse', 'portrait',
                'portrait reverse']
GRAPHICS_PARAMETERS = ['x_max', 'y_max', 'last_object_left', 'last_object_top',
                       'last_object_right', 'last_object_bottom']
TOUCH_STATES = ['enable', 'disable', 'default']
TOUCH_STATUSSES = ['invalid/notouch', 'press', 'release', 'moving']


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
            baud_rate (int): The baudrate for the communication
            debug (bool): Enable a check of whether there are bytes left in
                waiting after a reply has been fetched.
        """
        self.serial = serial.Serial(port=serial_device,
                                    baudrate=baudrate,
                                    bytesize=serial.EIGHTBITS,
                                    parity=serial.PARITY_NONE,
                                    stopbits=serial.STOPBITS_ONE,
                                    timeout=3)
        self.debug = debug

    def close(self):
        """Close the serial communication"""
        self.serial.close()

    def _send_command(self, command, reply_length=0):
        """Send a command and return status and reply

        Args:
            command (str): The command to send as a hex string  e.g. ``'001B'``
                for 0x001B
            reply_length (int): The length of the expected reply i.e. WITHOUT
                an acknowledge

        Returns:
            str: Reply is requested, otherwise None

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the requested length
        """
        self.serial.write(command.decode('hex'))
        reply_raw = self.serial.read(reply_length + 1)

        # Check if the an ACK is returned
        if reply_raw[0] != ACKNOWLEDGE:
            message = 'The command \'{0}\' failed'.format(command)
            raise PicasoException(message, exception_type='failed')

        # Extract the reply
        reply = None
        if reply_length > 0:
            if len(reply_raw) != reply_length + 1:
                message = 'The reply length {0} bytes, did not match the '\
                          'requested reply length {1} bytes'.format(
                              len(reply_raw) - 1, reply_length)
                raise PicasoException(message,
                                      exception_type='unexpected_reply')

            if self.debug:
                in_waiting = self.serial.inWaiting()
                if self.serial.inWaiting() != 0:
                    message = 'Wrong reply length. There are still {0} bytes '\
                              'left waiting on the serial port'.format(
                                  in_waiting)

            reply = reply_raw[1:]
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
            str: A 2 byte hex string e.g. ``'FFFF'``
        """
        # 5 bits for red and blue and 6 for green
        if type(color) == str:
            # Convert e.g. '#ffffff' to [1.0, 1.0, 1.0]
            color = [float(ord(x)) / 255 for x in color[1:7].decode('hex')]

        # '0001100011001001'
        #  |-r-||--g-||-b-|
        bitstring = '{:05b}{:06b}{:05b}'.format(int(color[0] * 31),
                                                int(color[1] * 63),
                                                int(color[2] * 31))
        # Turn the bit string into an integer
        as_int = int(bitstring, 2)
        # Format that into a hexstring with 2 bytes
        return '{:04X}'.format(as_int)

    @staticmethod
    def _from_16_bit_rgb(color):
        """Convert a `non regular 16 bit RGB
        <http://en.wikipedia.org/wiki/List_of_monochrome_and_RGB_palettes
        #16-bit_RGB>`_ to tuple of float e.g (1.0, 0.0, 1.0)

        Args:
            color (str): Color as 16 bit RGB string

        Returns:
            tuple: Color as tuple of floats e.g. (1.0, 0.0, 1.0)
        """
        # '0001100011001001'
        #  |-r-||--g-||-b-|
        bitstring = '{:08b}{:08b}'.format(*[ord(char) for char in color])
        out = []
        # Extract the r, g and b parts from the bitstring
        for start, end in ((0, 5), (5, 11), (11, 16)):
            # Convert to absolute int value
            as_int = int(bitstring[start: end], 2)
            # Convert to relative float (0.0 - 1.0)
            as_float = (float(as_int)) / (2 ** (end - start) - 1)
            out.append(as_float)
        return tuple(out)

    # TEXT AND STRING COMMANDS, section 5.1 in the manual
    def move_cursor(self, line, column):  # Section .1
        """Move the cursor to line, column and return boolean for success

        The actual position in which the cursor is placed is based on the
        current text parameters such as width and height

        Args:
            line (int): The line number to move the cursor to
            column (int): The column to move the cursor to

        Raises:
            PicasoException: If the command fails
        """
        command = 'FFE9{:04X}{:04X}'.format(line, column)
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
        command = '0018' + string.encode('hex') + '00'
        reply = self._send_command(command, 2)
        return int(reply.encode('hex'), 16)

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
        command = '001E{:02X}'.format(ord(character))
        reply = self._send_command(command, 2)
        return int(reply.encode('hex'), 16)

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
        command = '001D{:02X}'.format(ord(character))
        reply = self._send_command(command, 2)
        return int(reply.encode('hex'), 16)

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
        command = 'FFE7{0}'.format(self._to_16_bit_rgb(color))
        reply = self._send_command(command, 2)
        return self._from_16_bit_rgb(reply)

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
        command = 'FFE6{0}'.format(self._to_16_bit_rgb(color))
        reply = self._send_command(command, 2)
        return self._from_16_bit_rgb(reply)

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
        command = 'FFE4{:04X}'.format(factor)
        reply = self._send_command(command, 2)
        return int(reply.encode('hex'), 16)

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
        command = 'FFE3{:04X}'.format(factor)
        reply = self._send_command(command, 2)
        return int(reply.encode('hex'), 16)

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
        command = 'FFE2{:04X}'.format(pixels)
        reply = self._send_command(command, 2)
        return int(reply.encode('hex'), 16)

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
        command = 'FFE1{:04X}'.format(pixels)
        reply = self._send_command(command, 2)
        return int(reply.encode('hex'), 16)

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
        status = '0001' if status else '0000'
        command = TEXT_PROPERTY_TO_COMMAND[attribute] + status
        reply = self._send_command(command, 2)
        return True if reply == '\x00\x01' else False

    # GRAPHICS COMMANDS, section 5.2 in the manual
    def clear_screen(self):  # Sub-section .1
        """Clear the screen

        Raises:
            PicasoException: If the command fails
        """
        return self._send_command('FFCD')

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
        command = 'FFC8{:04X}{:04X}{:04X}{:04X}{color}'.format(
            *(start + end), color=self._to_16_bit_rgb(color)
        )
        return self._send_command(command)

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
        command = 'FFC5{:04X}{:04X}{:04X}{:04X}{color}'.format(
            *(top_left + bottom_right), color=self._to_16_bit_rgb(color)
        )
        return self._send_command(command)

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
        command = 'FFC4{:04X}{:04X}{:04X}{:04X}{color}'.format(
            *(top_left + bottom_right), color=self._to_16_bit_rgb(color)
        )
        return self._send_command(command)

    def move_origin(self, x, y):
        """Move the origin to a point, forming the basis for the next graphics
        or text command

        Args:
            x (int): X-coordinate for the new origin
            y (int): Y-coordinate for the new origin

        Raises:
            PicasoException: If the command fails
        """
        command = 'FFCC{:04X}{:04X}'.format(x, y)
        return self._send_command(command)
        

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
        command = 'FF9E{:04X}'.format(SCREEN_MODES.index(mode))
        reply = self._send_command(command, 2)
        return SCREEN_MODES[int(reply.encode('hex'), 16)]

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
        command = 'FFA6{:04X}'.format(GRAPHICS_PARAMETERS.index(parameter))
        reply = self._send_command(command, 2)
        return int(reply.encode('hex'), 16)

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
        command = 'FF39{:04X}{:04X}{:04X}{:04X}'.format(
            *(upper_left + bottom_right)
        )
        return self._send_command(command)

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
        command = 'FF38{:04X}'.format(mode)
        return self._send_command(command)

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
        reply = self._send_command('FF370000', 2)
        return TOUCH_STATUSSES[int(reply.encode('hex'), 16)]

    def touch_get_coordinates(self):  # Sub-section .3
        """Return the coordinates of the LAST touch event

        Returns:
            tuple: ``(x, y)`` where x and y are ints

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        # X
        reply = self._send_command('FF370001', 2)
        x_coord = int(reply.encode('hex'), 16)
        # Y
        reply = self._send_command('FF370002', 2)
        y_coord = int(reply.encode('hex'), 16)

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
        reply = self._send_command('001A', 12)
        # The display model is prefixed with 0x00 0x0A which is stripped
        return reply[2:]

    def get_spe_version(self):  # Sub-section .4
        """Get the version of the Serial Platform Environment

        Returns:
            str: The version or ``None`` on failure

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the expected length
        """
        reply = self._send_command('001B', 2)
        reply = [ord(x) for x in reply]
        return '{}.{}'.format(*reply)


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
        origin_y = (self.button_height - self.char_height) / 2 +\
                   self.top_left[1]
        origin_y = max(origin_y, self.top_left[1])

        # Calculate text origin x-coordinate dependent on justification
        if self.text_justify == 'left':
            # If left HERE
            if self.left_justify_indent:
                origin_x = self.top_left[0] + self.left_justify_indent
            else:
                origin_x = self.top_left[0] + self.char_width / 2
        else:
            text_width = len(self.text) * self.char_width
            origin_x = (self.button_width - text_width) / 2 + self.top_left[0]
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
