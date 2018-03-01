"""This module contains integration tests for the 4D Systems LCD display
driver
"""

from __future__ import division, print_function, unicode_literals
from builtins import (
         bytes, dict, int, list, object, range, str,
         ascii, chr, hex, input, next, oct, open,
         pow, round, super,
         filter, map, zip)


import time
from PyExpLabSys.drivers.four_d_systems import PicasouLCD28PTU
PICASO = None


def text_commands():
    """Test the text and string commands, section 5.1 of the manual"""
    print('\nTEXT COMMANDS')

    test_text_move_and_put_string()
    test_text_char_width_and_height()
    test_text_color_width_height()
    test_text_gaps()
    test_text_attributes()


def test_text_move_and_put_string():
    """Test move and put string"""
    print('\nMove cursor to positions 0, 0;  1, 1 and 2, 3 and write the '\
        'string \'CINF\'')
    PICASO.clear_screen()
    for index in range(3):
        PICASO.move_cursor(index, index)
        PICASO.put_string('CINF')
    accept()


def test_text_char_width_and_height():
    """Test get character width and height"""
    print('\nGet character width and height. Should be 8 and 12 for the '\
        'standard font')
    width = PICASO.character_width('l')
    height = PICASO.character_height('l')
    print('Width, height: {0},{1}'.format(width, height))
    accept()


def test_text_color_width_height():
    """Test foreground color, width and height"""
    print('\nTest text foreground color (red), width (x2), height (x2), '\
        'combined width and height (x2)')
    PICASO.clear_screen()
    PICASO.put_string('CINF')
    # Color
    PICASO.move_cursor(1, 0)
    PICASO.text_foreground_color((1, 0, 0))
    PICASO.put_string('CINF')
    # Width
    PICASO.move_cursor(2, 0)
    PICASO.text_width(2)
    PICASO.put_string('CINF')
    # Height
    PICASO.move_cursor(3, 0)
    PICASO.text_width(1)
    PICASO.text_height(2)
    PICASO.put_string('CINF')
    # combined width and height
    PICASO.text_height(1)
    PICASO.move_cursor(5, 0)
    PICASO.text_factor(2)
    PICASO.put_string('CINF')
    accept()


def test_text_gaps():
    """Test gaps"""
    print('\nTest text x and y gap. First is normal, second is x gap 4, '\
        'third is y gap 4')
    PICASO.clear_screen()
    PICASO.put_string('CINF')
    PICASO.move_cursor(1, 0)
    PICASO.put_string('CINF')
    PICASO.text_x_gap(4)
    PICASO.move_cursor(2, 0)
    PICASO.put_string('CINF')
    PICASO.move_cursor(3, 0)
    PICASO.put_string('CINF')
    PICASO.text_x_gap(0)
    PICASO.text_y_gap(4)
    PICASO.move_cursor(4, 0)
    PICASO.put_string('CINF')
    PICASO.move_cursor(5, 0)
    PICASO.put_string('CINF')
    accept()


def test_text_attributes():
    """Test text attributes"""
    attributes = ['bold', 'inverse', 'italic', 'opacity', 'underline']
    print('\nTest the text attributes {0}, once on each line after a normal '\
        'one'.format(attributes))
    PICASO.clear_screen()
    PICASO.put_string('CINF')
    for index, attribute in enumerate(attributes):
        PICASO.move_cursor(index+1, 0)
        PICASO.text_attribute(attribute)
        PICASO.put_string('CINF')
        PICASO.text_attribute(attribute, status=False)
    accept()


def graphics_commands():
    """Test the graphics commands"""
    print('\nGRAPHICS COMMANDS')
    #test_graphics_screen_rotation()
    test_draw_line_graphics_props()


def test_graphics_screen_rotation():
    """Test the different screen rotations"""
    print('\nTest the 4 different screen rotations, accept each one')
    for rotation in ['landscape', 'landscape reverse', 'portrait',
                     'portrait reverse']:
        PICASO.clear_screen()
        print('= ' + rotation)
        PICASO.screen_mode(rotation)
        PICASO.put_string('CINF')
        accept()


def test_draw_line_graphics_props():
    """Test draw line and get graphics properties"""
    print('\nTest draw line (50, 50), (170, 170), \'#0000ff\'')
    PICASO.clear_screen()
    PICASO.draw_line((50, 50), (170, 170), '#0000ff')
    accept()

    graphics_parameters = ['x_max', 'y_max', 'last_object_left',
                           'last_object_top', 'last_object_right',
                           'last_object_bottom']
    print('\nTest get graphics parameters {0}.\nNOTE The \'last_object_*\' '\
        'properties does not make much sense. Unknown reason.'.format(
            graphics_parameters))
    for parameter in graphics_parameters:
        print('# {0} = {1}'.format(
            parameter,
            PICASO.get_graphics_parameters(parameter)
        ))
        accept()


def touch_commands():
    """Test the touch commands"""
    print('\nTEST THE TOUCH COMMANDS')
    test_touch_region()
    test_touch_set()


def test_touch_region():
    """Test the touch set region command (and get status and coordinates)"""
    print('\nTest the touch set region command')
    print('Test set touch region along left edge. Check that \'press\', '\
        '\'moving\' and \'release\' event can be generated there and only '\
        '\'invalid\' on the rest of the screen. Press enter to start')
    PICASO.touch_set('enable')
    PICASO.touch_detect_region((0, 0), (59, 319))
    input()
    for _ in range(25):
        time.sleep(0.2)
        print(PICASO.touch_get_status())
        print(PICASO.touch_get_coordinates())
    accept()


def test_touch_set():
    """Test the touch set command (and get status and coordinates)"""
    print('\nTest the touch set command')

    print('Test \'default\'. Restricts the touch region, then sets to the '\
        'default, which is everything. So it should be possible to create '\
        'touch events all over. Press enter to start')
    PICASO.touch_set('enable')
    PICASO.touch_detect_region((0, 0), (59, 319))
    PICASO.touch_set('default')
    input()
    for _ in range(25):
        time.sleep(0.2)
        print(PICASO.touch_get_status())
        print(PICASO.touch_get_coordinates())
    accept()

    print('Test \'disable\', try and touch the screen, all statusses should '\
        'be invalid/notouch. Press enter to start, active for 3 seconds.')
    input()
    PICASO.touch_set('disable')
    for _ in range(25):
        time.sleep(0.2)
        print(PICASO.touch_get_status())
        print(PICASO.touch_get_coordinates())
    accept()

    print('Test \'enable\', try and touch the screen, you should now be able '\
        'to get \'press\', \'moving\' and \'release\' states. Press enter to '\
        'start, active for 3 seconds.')
    input()
    PICASO.touch_set('enable')
    for _ in range(25):
        time.sleep(0.2)
        print(PICASO.touch_get_status())
        print(PICASO.touch_get_coordinates())
    accept()


def system_commands():
    """Test system commands"""
    print('\nTEST SYSTEM COMMANDS')
    test_get_display_model()
    test_get_spe_version()


def test_get_display_model():
    """Test the get display model command"""
    print('\nTest the get display model command. Should return an '\
        'understandable model.')
    print(PICASO.get_display_model())
    accept()


def test_get_spe_version():
    """Test the get SPE version command"""
    print('\nTest the get SPE version command. Should return a ?.? version '\
        'number.')
    print(PICASO.get_spe_version())
    accept()


def accept():
    """Ask the user if the result is as desired and raise exception if it is
    not
    """
    answer = None
    while answer not in ['', 'n']:
        message = 'Is the result acceptable? '\
                  'Press Enter to accept or \'n\' and Enter to reject:'
        answer = input(message)
    if answer == 'n':
        message = 'Test result not accepted'
        raise Exception(message)


def main():
    """Gathers and executes the different test sections"""
    # pylint: disable=global-statement
    global PICASO
    PICASO = PicasouLCD28PTU(serial_device='/dev/ttyUSB0', baudrate=9600,
                             debug=True)
    try:
        text_commands()
        graphics_commands()
        touch_commands()
        system_commands()
        # pylint: disable=broad-except
    except Exception:
        import traceback
        traceback.print_exc()
        PICASO.close()


if __name__ == '__main__':
    main()
