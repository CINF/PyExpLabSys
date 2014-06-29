#!/usr/bin/env python
# pylint: disable=W0142

"""Drivers for the 4d systems displays

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
    https://cinfwiki.fysik.dtu.dk/cinfwiki/Equipment#Picaso_uLCD-28PTU
    or online at:
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


class PicasoCommon(object):
    """Implementation of the common parts of the serial communication to the
    Picaso devices
    """

    def __init__(self, serial_device='/dev/ttyUSB0', baudrate=9600,
                 check_in_waiting=True):
        """Initialize the driver

        The serial device and the baudrate are configurable, as described
        below. The rest of the serial communication parameters are; bytesize: 8
        bits, parity: None, stopbits: one (as per the manual) and a timeout of
        3 seconds.

        Args:
            serial_device (str): The serial device to open communication on
            baud_rate (int): The baudrate for the communication
            check_in_waiting (bool): There if there are bytes left in waiting
                after a reply has been fetched. This will make it easier to
                find wrong reply lenghts, but will send one extra serial request
                per command
        """
        self.serial = serial.Serial(port=serial_device,
                                    baudrate=baudrate,
                                    bytesize=serial.EIGHTBITS,
                                    parity=serial.PARITY_NONE,
                                    stopbits=serial.STOPBITS_ONE,
                                    timeout=3)
        self.check_in_waiting = check_in_waiting

    def close(self):
        """Close the serial communication"""
        self.serial.close()

    def _send_command_get_reply(self, command, reply_length=0):
        """Send a command and return status and reply

        Args:
            command (str): The command to send as a hex string  e.g. ``'001B'``
                for 0x001B
            reply_length (int): The length of the expected reply i.e. WITHOUT
                an acknowledge

        Returns:
            str: reply is requested, otherwise None

        Raises:
            PicasoException: If the command fails or if the reply does not have
                the requested length
        """
        self.serial.write(command.decode('hex'))
        reply_raw = self.serial.read(reply_length + 1)

        # Check if the an ACK is returned
        if reply_raw[0] != ACKNOWLEDGE:
            message = 'The command \'{0}\' failed'.format(command)
            raise PicaosException(message, exception_type='failed')

        # Extract the reply
        reply = None
        if reply_length > 0:
            if len(reply_raw) != reply_length + 1:
                message = 'The reply length {0} bytes, did not match the '\
                          'requested reply length {1} bytes'.format(
                              len(reply_raw) - 1, reply_length)
                raise PicasoException(message,
                                      exception_type='unexpected_reply')

            if self.check_in_waiting:
                in_waiting = self.serial.inWaiting()
                if self.serial.inWaiting() != 0:
                    message = 'Wrong reply length. There are still {0} bytes '\
                              'left waiting on the serial port'.format(
                                  in_waiting)

            reply = reply_raw[1:]
        return reply

    def _send_command(self, command):
        """Send command and return success

        Args:
            command (str): The command to send in hex e.g. ``'001B'`` for
            0x001B

        Returns:
            bool: Success
        """
        success, _, _ = self._send_command_get_reply(command)
        return success

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

        Returns:
            bool: Success
        """
        command = 'FFE9{:04X}{:04X}'.format(line, column)
        return self._send_command(command)

    def put_string(self, string):  # Section .3
        """Write a string on the display

        .. note:: It has not been investigated whether characters outside of
            ASCII can be used. If that becomes necessary, try, and possibly
            consult the manual

        Args:
            string (str): Ascii string to write, max length 511 chars

        Returns:
            int: The number of bytes written on success or ``None`` on failure
        """
        command = '0018' + string.encode('hex') + '00'
        success, reply, answer_good = \
            self._send_command_get_reply(command, 2)
        if success and answer_good:
            return int(reply.encode('hex'), 16)

    def character_width(self, character):  # Sub-section .4
        """Get the width of a character in pixels with the current font

        Args:
            character (str): Character to get the width of

        Returns:
            int: The width in pixels or None on failure
        """
        if len(character) != 1:
            raise ValueError('character must be a string of length 1')
        command = '001E{:02X}'.format(ord(character))
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
            return int(reply.encode('hex'), 16)

    def character_height(self, character):  # Sub-section .5
        """Get the height of a character in pixels with the current font

        Args:
            character (str): Character to get the height of

        Returns:
            int: The height in pixels or None on failure
        """
        if len(character) != 1:
            raise ValueError('character must be a string of length 1')
        command = '001D{:02X}'.format(ord(character))
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
            return int(reply.encode('hex'), 16)

    def text_foreground_color(self, color):  # Sub-section .6
        """Sets the foreground color of the text

        Args:
            color (tuple or string): 24 bit RGB HTML hex string e.g. '#ffffff'
                or RGB tuple or floats e.g. (1.0, 1.0, 1.0)

        Returns:
            tuple: Previous color as tuple of floats e.g. (1.0, 1.0, 1.0) or
                None on failure
        """
        command = 'FFE7{0}'.format(self._to_16_bit_rgb(color))
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
            return self._from_16_bit_rgb(reply)

    def text_width(self, factor):  # Sub-section .9
        """Sets the text width

        Args:
            factor (int): Width multiplier (1-16) relative to default width

        Returns:
            int: Previous width multiplier or None on failure
        """
        command = 'FFE4{:04X}'.format(factor)
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
            return int(reply.encode('hex'), 16)

    def text_height(self, factor):  # Sub-section .10
        """Sets the text height

        Args:
            factor (int): Height multiplier (1-16) relative to default height

        Returns:
            int: Previous height multiplier or None on failure
        """
        command = 'FFE3{:04X}'.format(factor)
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
            return int(reply.encode('hex'), 16)


    def text_factor(self, factor):  # Sub-section .9 and .10
        """Sets the text width and height
        Args:
            factor (int): Width and height multiplier (1-16) relative to
                default width and height

        Returns:
            tuple: Previous width and height multipliers or None on failure
        """
        previous_width = self.text_width(factor)
        previous_height = self.text_height(factor)
        if None not in [previous_width, previous_height]:
            return (previous_width, previous_height)

    def text_x_gap(self, pixels):  # Sub-section .11
        """Sets the horizontal gap between chars in pixels

        Args:
            pixels (int): The requested horizontal gap in pixels

        Return:
            int: The previous horizontal gap in pixels
        """
        command = 'FFE2{:04X}'.format(pixels)
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
            return int(reply.encode('hex'), 16)

    def text_y_gap(self, pixels):  # Sub-section .11
        """Sets the vertical gap between chars in pixels

        Args:
            pixels (int): The requested vertical gap in pixels

        Return:
            int: The previous vertical gap in pixels
        """
        command = 'FFE1{:04X}'.format(pixels)
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
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
            bool: The previous status or None on failure

        Raises:
            ValueError
        """
        if attribute not in TEXT_PROPERTY_TO_COMMAND:
            message = 'Attribute \'{0}\' unknown. Valid attributes are {1}'\
                .format(attribute, TEXT_PROPERTY_TO_COMMAND.keys())
            raise ValueError(message)
        status = '0001' if status else '0000'
        command = TEXT_PROPERTY_TO_COMMAND[attribute] + status
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
            return True if reply == '\x00\x01' else False
        

    # GRAPHICS COMMANDS, section 5.2 in the manual
    def clear_screen(self):  # Sub-section .1
        """Clear the screen

        Returns:
            bool: Success
        """
        return self._send_command('FFCD')

    def draw_line(self, start, end, color):  # Sub-section .5
        """Draw a line from x1, y1 to x2, y2 and return boolean for success

        Args:
            start (tuple): Start point (x, y), where x and y are ints
            end (tuple): End point (x, y), where x and y are ints
            color (tuple or string): 24 bit RGB HTML hex string e.g. '#ffffff'
                or RGB tuple or floats e.g. (1.0, 1.0, 1.0)

        Returns:
            bool: Success
        """
        command = 'FFC8{:04X}{:04X}{:04X}{:04X}{color}'.format(
            *(start + end), color=self._to_16_bit_rgb(color)
        )
        return self._send_command(command)

    def screen_mode(self, mode):  # Sub-section 34
        """Sets the screen mode

        Args:
            mode (str): The mode for the screen. Can be either ``'landscape'``,
                ``'landscape reverse'``, ``'portrait'`` or
                ``'portrait reverse'``

        Returns:
            str: Returns previous screen mode on success or ``None`` on failure
        """
        modes = ['landscape', 'landscape reverse', 'portrait',
                 'portrait reverse']
        command = 'FF9E{:04X}'.format(modes.index(mode))
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
            return modes[int(reply.encode('hex'), 16)]

    def get_graphics_parameters(self, parameter):  # Sub-section 38
        """Gets graphics parameters

        Args:
            parameter (str): The parameter to fetch, can be ``'x_max'`` for
            the x resolution under the current orientation, ``'y_max'`` for
            the y resolution under the current orientation,
            ``'last_object_left'``, ``'last_object_top'``,
            ``'last_object_right'``, ``'last_object_bottom'`` for the relevant
            parameter for the last object.

        Returns:
          int: The requested parameter or ``None`` on error
        """
        modes = ['x_max', 'y_max', 'last_object_left', 'last_object_top',
                 'last_object_right', 'last_object_bottom']
        command = 'FFA6{:04X}'.format(modes.index(parameter))
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
            return int(reply.encode('hex'), 16)

    # TOUCH SCREEN COMMANDS, section 5.8 in the manual
    def touch_detect_region(self, upper_left, bottom_right):  # Sub-section .1
        """Specify a touch detection region

        Args:
            upper_left (tuple): ``(x, y)`` for the upper left corner, where x
                and y are ints
            bottom_right (tuple): ``(x, y)`` for the lower right corner, where
                x and y are ints

        Returns:
            bool: Success
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

        Returns:
            bool: Success
        """
        mode = {'enable': 0, 'disable': 1, 'default': 2}[mode]
        command = 'FF38{:04X}'.format(mode)
        return self._send_command(command)

    def touch_get_status(self):  # Sub-section .3
        """Return the state of the touch screen

        Returns:
            str: The state of the touch screen, can be either
            ``'invalid/notouch'``, ``'press'``, ``'release'``, ``'moving'`` or
            ``None`` on error
        """
        command = 'FF370000'
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
            statusses = ['invalid/notouch', 'press', 'release', 'moving']
            return statusses[int(reply.encode('hex'), 16)]

    def touch_get_coordinates(self):  # Sub-section .3
        """Return the coordinates of the LAST touch event

        Returns:
            tuple: ``(x, y)`` where x and y are ints or ``None`` on failure
        """
        out = [None, None]
        # X
        command = 'FF370001'
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
            out[0] = int(reply.encode('hex'), 16)
        # Y
        command = 'FF370002'
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
            out[1] = int(reply.encode('hex'), 16)

        if None not in out:
            return tuple(out)

    # SYSTEM COMMANDS, section 5.10 in the manual
    def get_display_model(self):  # Sub-section .3
        """Get the display model

        Returns:
            str: The display model or ``None`` on failure
        """
        success, reply, good = self._send_command_get_reply('001A', 12)
        if success and good:
            # The display model is prefixed with 0x00 0x0A which is stripped
            return repr(reply[2:])

    def get_spe_version(self):  # Sub-section .4
        """Get the version of the Serial Platform Environment

        Returns:
            str: The version or ``None`` on failure
        """
        succes, reply, good = self._send_command_get_reply('001B', 2)
        reply = [ord(x) for x in reply]
        if succes and good:
            return '{}.{}'.format(*reply)


class PicasoException(Exception):
    """Exception for Picaso communication

    The ``exception_type`` parameter can be either, ``'failed'`` or
    ``'unexpected_reply'``
    """

    def __init__(self, message, exception_type):
        super(PicasoException, self).__init__(message)
        self.exception_type = exception_type


class PicasouLCD28PTU(PicasoCommon):
    """Driver for the Picaso 28 PTU Pi LCD display

    For details on the methods that can be called on this class see the
    documentation for FIXME PicasoCommon
    """

    def __init__(self, serial_device='/dev/ttyUSB0', baudrate=9600,
                 check_in_waiting=True):
        super(PicasouLCD28PTU, self).__init__(serial_device, baudrate)


def test_single():
    """Use the various methods to test the driver"""
    import time
    picaso = PicasouLCD28PTU(serial_device='/dev/ttyUSB0', baudrate=9600)
    try:
        print '\nGet the display model'
        print picaso.get_display_model()
        print "\nClear Screen"
        print picaso.clear_screen()

        # TEST WIDTH AND HEIGHT COMMANDS
        # TEST GAP COMMANDS
        # TEST TEXT PROPERTY COMMANDS
        # Put command here

        print '\nPut string \'Hallo\''
        print picaso.put_string('Hallo')
        print "\nSet bold"
        print picaso.text_attribute('inverse')
        print "\nSet bold"
        print picaso.text_attribute('inverse')
        print '\nPut string \'World\''
        print picaso.put_string('World')

        print '\nWait 5 sec'
        time.sleep(5)
        print "Close"
        picaso.close()
    except Exception as exception:
        import traceback
        traceback.print_exc()
        picaso.close()
        raise exception


def test():
    """Use the various methods to test the driver"""
    import time
    picaso = PicasoCommon(serial_device='/dev/ttyUSB0', baudrate=9600)
    try:
        print "Ask for SPE version"
        print picaso.get_spe_version()

        print '\nGet the display model'
        print picaso.get_display_model()
        print "\nClear Screen"
        print picaso.clear_screen()
        print '\nResolution before rotation'
        print picaso.get_graphics_parameters('x_max'),\
            picaso.get_graphics_parameters('y_max')
        print '\nSet landscape mode'
        print picaso.screen_mode('landscape')
        print '\nResolution after rotation'
        print picaso.get_graphics_parameters('x_max'),\
            picaso.get_graphics_parameters('y_max')
        print '\nPut string \'Hallo\''
        print picaso.put_string('Hallo')
        print '\nMove to 1,1'
        print picaso.move_cursor(1, 1)
        print '\nPut string \'World!\''
        print picaso.put_string('World!')
        print '\nDraw line'
        print picaso.draw_line((50, 50), (170, 170), '#0000ff')

        print '\nEnable the touch screen'
        #print picaso.touch_set('default')
        print picaso.touch_set('enable')
        print '\nSet touch area in upper left corner'
        print picaso.touch_detect_region((0, 0), (100, 100))
        while False:
            print '\nGet the touch status'
            print picaso.touch_get_status()
            print '\nGet the coordinates'
            print picaso.touch_get_coordinates()
            time.sleep(0.3)

        print '\nWait 5 sec'
        time.sleep(5)
        print "Close"
        picaso.close()
    except Exception as exception:
        import traceback
        traceback.print_exc()
        picaso.close()
        raise exception


if __name__ == '__main__':
    test_single()
