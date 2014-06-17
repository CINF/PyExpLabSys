#!/usr/bin/env python
# pylint: disable=W0142

""" Drivers for the 4d systems displays

NOTE 1. Only a small sub-set of the specification is plemented, but with the
available examples it should be real easy to add more commands.

NOTE 2. An internal method '_to_16_bit_rgb' exists to convert a HTML hex color
code or an RGB tuple of floats to the irregular 16 bit RGB color scale this
device use. It should make working with colors a lot easier.

NOTE 3. The displays must be activated for serial communication. At present the
only way we know how to do that, is to follow the procedure described in the
serial specification, which involves taking it past a Windown program.

NOTE 4. At present only communication via the USB connection has been tested.
For communication directly via the internal connection on the Raspberry Pi it
may be necessary to do some preparation in order to free the pins up for serial
communication.

Docs for this implementation are on the wiki at:
https://cinfwiki.fysik.dtu.dk/cinfwiki/Equipment#Picaso_uLCD-28PTU
or online at:
http://www.4dsystems.com.au/product/4D_Workshop_4_IDE/downloads
"""


import serial

ACKNOWLEDGE = '\x06'


class PicasoCommon(object):
    """Implementation of the common parts of the serial communication to the
    Picaso devices
    """

    def __init__(self, serial_device='/dev/ttyUSB0', baudrate=9600):
        self.serial = serial.Serial(port=serial_device,
                                    baudrate=baudrate,
                                    bytesize=serial.EIGHTBITS,
                                    parity=serial.PARITY_NONE,
                                    stopbits=serial.STOPBITS_ONE,
                                    timeout=3)

    def close(self):
        """Close the serial communication"""
        self.serial.close()

    def _send_command_get_reply(self, command, reply_length=0, output='raw'):
        """Send a command and return status and reply

        Args:
        command (str) the command to send as a hex string  e.g. '001B' for 0x001B
        reply_length  the length of the expected reply, i.e. WITHOUT an
                      acknowledge
        output        the format for the reply, possibly value are 'raw' (default)
                      which returns a hex string and 'int' which returns a list
                      of ints

        Returns:
        (status, reply, answer_good)
        where
        status       is a boolean representing the succes
        reply        is the reply as a string (None if none is requested)
        answer_good  boolean for whether the answer has the correct length (or
                     None if no reply is requested)
        """
        self.serial.write(command.decode('hex'))
        reply_raw = self.serial.read(reply_length + 1)
        succes = False
        reply = None
        answer_good = None
        if len(reply_raw) > 0:
            succes = reply_raw[0] == ACKNOWLEDGE
            if reply_length > 0:
                reply = reply_raw[1:]
                if output == 'int':
                    reply = [ord(x) for x in reply]
                answer_good = len(reply_raw) == reply_length + 1
        #print succes, repr(reply), answer_good
        return succes, reply, answer_good

    def _send_command(self, command):
        """Send command

        Args:
        command (str)    the command to send in hex e.g. '001B' for 0x001B

        Returns
        success (boolean)
        """
        success, _, _ = self._send_command_get_reply(command)
        return success

    @staticmethod
    def _to_16_bit_rgb(color):
        """Convert a color to the non regular 16 bit RGB
        http://en.wikipedia.org/wiki/List_of_monochrome_and_RGB_palettes#16-bit_RGB

        Args:
        color  24 bit RGB HTML hex string e.g. '#ffffff' or RGB tuple or floats e.g.
               (1.0, 1.0, 1.0)

        Return a 2 byte hex string e.g. 'FFFF'
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

    # TEXT AND STRING COMMANDS, section 5.1 in the manual
    def move_cursor(self, line, column):  # Section .1
        """Move the cursor to line, column and return boolean for success

        The actual position in which the cursor is placed is based on the
        current text parameters such as width and height
        """
        command = 'FFE9{:04X}{:04X}'.format(line, column)
        return self._send_command(command)

    def put_string(self, string):  # Section .3
        """Output a string and return number of bytes written on succes or None
        on failure

        Args:
        string    Ascii string to write, max length 511 chars
        """
        command = '0018' + string.encode('hex') + '00'
        success, reply, answer_good = \
            self._send_command_get_reply(command, 2)
        if success and answer_good:
            return int(reply.encode('hex'), 16)

    # GRAPHICS COMMANDS, section 5.2 in the manual
    def clear_screen(self):  # Sub-section .1
        """Clear the screen and returns boolean for succes"""
        return self._send_command('FFCD')

    def draw_line(self, start, end, color):  # Sub-section .5
        """Draw a line from x1, y1 to x2, y2 and return boolean for success

        Args:
        start (tuple)  Start point (x, y)
        end (tuple)    End point (x, y)
        color (tuple or string)  24 bit RGB HTML hex string e.g. '#ffffff' or
                       RGB tuple or floats e.g. (1.0, 1.0, 1.0)
        """
        command = 'FFC8{:04X}{:04X}{:04X}{:04X}{color}'.format(
            *(start + end), color=self._to_16_bit_rgb(color)
        )
        return self._send_command(command)

    def screen_mode(self, mode):  # Sub-section 34
        """Sets the screen mode

        Args:
          mode (str): The mode for the screen. Can be either 'landscape',
          'landscape reverse', 'portrait' or 'portrait reverse'

        Returns:
          bool: Returns previous screen mode on success of None on failure
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
          parameter (str): The parameter to fetch, can be 'x_max' for the x
          resolution under the current orientation, 'y_max' for the y resolution
          under the current orientation, 'last_object_left', 'last_object_top',
          'last_object_right', 'last_object_bottom' for the relevant parameter
          for the last object.

        Returns:
          int: The requested parameter or None on error
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
          upper_left (tuple): X, y for the upper left corner
          bottom_right (tuple): X, y for the lower right corner

        Returns:
          bool: True is successful.
        """
        command = 'FF39{:04X}{:04X}{:04X}{:04X}'.format(
            *(upper_left + bottom_right)
        )
        return self._send_command(command)

    def touch_set(self, mode):  # Sub-section .2
        """Set touch screen related parameters

        Args:
          mode (string): The mode to set. It can be either 'enable'; which
          enables and initializes the touch screen, 'disable' which disables
          the touch screen or 'default' which will reset the current active
          region to the default which is the full screen area.
        """
        mode = {'enable': 0, 'disable': 1, 'default': 2}[mode]
        command = 'FF38{:04X}'.format(mode)
        return self._send_command(command)

    def touch_get_status(self):  # Sub-section .3
        """Return the state of the touch screen

        Returns:
          str: The state of the touch screen, can be either 'invalid/notouch',
          'press', 'release', 'moving' or None on error
        """
        command = 'FF370000'
        success, reply, answer_good = self._send_command_get_reply(command, 2)
        if success and answer_good:
            statusses = ['invalid/notouch', 'press', 'release', 'moving']
            return statusses[int(reply.encode('hex'), 16)]

    def touch_get_coordinates(self):  # Sub-section .3
        """Return the coordinates of the LAST touch event

        Returns:
          tuple: (x, y) or None on failure
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
        """Return the display model or None or failure"""
        success, reply, good = self._send_command_get_reply('001A', 12)
        if success and good:
            # The display model is prefixed with 0x00 0x0A which is stripped
            return repr(reply[2:])

    def get_spe_version(self):  # Sub-section .4
        """Return the version of the Serial Platform Environment"""
        succes, reply, good = self._send_command_get_reply('001B', 2, 'int')
        if succes and good:
            return '{}.{}'.format(*reply)


def test():
    import time
    """Text and draw test"""
    picaso = PicasoCommon(serial_device='/dev/ttyAMA0', baudrate=9600)
    try:
        print "Ask for SPE version"
        print picaso.get_spe_version()

        print '\nGet the display model'
        print picaso.get_display_model()
        print "\nClear Screen"
        print picaso.clear_screen()
        print '\nResolution before rotation'
        print picaso.get_graphics_parameters('x_max'), picaso.get_graphics_parameters('y_max')
        print '\nSet landscape mode'
        print picaso.screen_mode('landscape')
        print '\nResolution after rotation'
        print picaso.get_graphics_parameters('x_max'), picaso.get_graphics_parameters('y_max')
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
    test()
