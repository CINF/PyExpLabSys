import sys
import os
import time
import textwrap
import select
import threading
from queue import Empty
from PyExpLabSys.drivers.four_d_systems import PicasouLCD28PTU, to_ascii_utf8
from PyExpLabSys.drivers.deltaco_TB_298 import detect_keypad_device, ThreadedKeypad, KEYS_TO_CHARS
from VEXTA_ASX66A import ZY_raster_pattern, connect_Z_Y

from PyExpLabSys.common.supported_versions import python3_only
python3_only(__file__)

# Test specific
#from PIL import Image

__VERSION__ = '1.0'
__AUTHOR__ = 'Jakob Ejler'


class TUI(object):
    """Class to handle all drawing to display"""

    def __init__(self, picaso, box_color=(0.6, 0.6, 0.6), text_color=(0.0, 1.0, 0.0), version=__VERSION__):
        self.picaso = picaso
        self.box_color = box_color
        self.text_color = text_color
        self.char_width = self.picaso.character_width('.')
        self.char_height = self.picaso.character_height('.')
        self.size = (320, 240)
        self.gap = 2
        self.toggled = {
                'men': False,
                'tog': False,
                'del': False,
                }
        self.locator = -1
        self.sublocator = 0
        self.last_key = ''

        self.motor = 'Y'
        self.position = {'Y': Y.get_position(),
                         'Z': Z.get_position()}
        self.motion_marker = ''

        # Draw header
        self.picaso.move_cursor(0,0)
        self.picaso.text_attribute('italic', status=True)
        self.picaso.put_string('PREP chamber manipulator, v{}'.format(__VERSION__))
        self.picaso.text_attribute('italic', status=False)

        # Define Box 1 (for position display of motors)
        self.box1 = {
                'origin': (2, 2 + self.char_height + 6),
                'width': 39,
                'lines': 3,
                }
        self.subbox1 = {
                'origin': (
                    self.box1['origin'][0] + len('position x: ')*self.char_width,
                    self.box1['origin'][1]
                    ),
                'width': self.box1['width'] - len('position x: '),
                'lines': self.box1['lines'],
                }
        self.draw_box(self.box1, action=['draw', 'clear'])
        self.write_box1(update_values_only=False)

        # Define Box 2 (for display of menus and information)
        self.box2 = {
                'origin': (
                    2,
                    self.box1['origin'][1] + self.box1['lines']*self.char_height+self.gap*4
                    ),
                'width': 35,
                'lines': 10,
                }
        self.draw_box(self.box2, action=['draw', 'clear'])

        # Define Box 3 (small narrow display of buttons and keys)
        self.box3 = {
                'origin': (
                    self.box2['origin'][0] + self.box2['width']*self.char_width + self.gap*4,
                    self.box1['origin'][1] + self.box1['lines']*self.char_height + self.gap*4
                    ),
                'width': 3,
                'lines': 10,
                }
        self.draw_box(self.box3, action=['draw', 'clear'])
        self.write_box3()

        # Define Box 4 (small wide display for retrieval of user inputs or info display)
        self.box4 = {
                'origin': (
                    2,
                    self.box2['origin'][1] + self.box2['lines']*self.char_height + self.gap*4
                    ),
                'width': 39,
                'lines': 2,
                }
        self.draw_box(self.box4, action=['draw', 'clear'])
        self.main_screen()

    def draw_box(self, box, action=['clear']):
        
        (x1, y1) = box['origin']
        x2, y2 = x1 + box['width']*self.char_width, y1 + box['lines']*self.char_height
        for act in action:
            if act == 'draw':
                self.picaso.draw_rectangle((x1-2, y1-2), (x2+2, y2+2), self.box_color)
            elif act == 'clear':
                self.picaso.draw_filled_rectangle((x1, y1), (x2, y2), (0,0,0))

    def write_box1(self, motion=False, update_values_only=True):
        """Update BOX1
        motion (bool): if True - add dots after selected motor to indicate motion in progress.
        update_values_only (bool): if True - only update position values (do not erase and draw text)
        """

        # Clear BOX1 and write strings
        self.picaso.text_factor(1)
        if not update_values_only:
            self.draw_box(self.box1, action=['clear'])
            (x, y) = self.box1['origin']
            self.picaso.move_origin(x, y)
            self.picaso.put_string('Position Z: \n')
            self.picaso.put_string('Position Y: ')

        # Clear SUBBOX1 and add values
        if motion:
            self.motion_marker += '.'
            if len(self.motion_marker) > 3:
                self.motion_marker = ''
        else:
            self.motion_marker = ''
        self.draw_box(self.subbox1, action=['clear'])
        (x,y) = self.subbox1['origin']
        self.picaso.move_origin(x, y)
        strings = {'Y': '', 'Z': ''}
        for i in ['Y', 'Z']:
            if i == self.motor:
                strings[i] = str(self.position[i]) + ' ' + self.motion_marker
            else:
                strings[i] = str(self.position[i])
        self.picaso.put_string(strings['Z'] + '\n')
        self.picaso.put_string(strings['Y'])

    def write_box3(self):
        """Update BOX3 """
        
        (x, y) = self.box3['origin']
        self.draw_box(self.box3, action=['clear'])
        self.picaso.move_origin(x, y)
        # TOGGLE INDICATOR
        if self.toggled['tog']:
            old_setting = self.picaso.text_attribute('inverse', status=True)
            self.picaso.put_string('TOG\n')
            self.picaso.text_attribute('inverse', status=old_setting)
        else:
            self.picaso.put_string('TOG\n')
        # MENU INDICATOR
        if self.toggled['men']:
            old_setting = self.picaso.text_attribute('inverse', status=True)
            self.picaso.put_string('MEN\n')
            self.picaso.text_attribute('inverse', status=old_setting)
        else:
            self.picaso.put_string('MEN\n')
        # DELETE INDICATOR
        if self.toggled['del']:
            old_setting = self.picaso.text_attribute('inverse', status=True)
            self.picaso.put_string('DEL\n')
            self.picaso.text_attribute('inverse', status=old_setting)
        else:
            self.picaso.put_string('DEL\n')
        # Locators
        self.picaso.put_string('\n {}\n {}\n {}'.format(self.locator, self.sublocator, self.last_key))

    def write_box4(self, string):
        """Print string in BOX4 
        Input:
        string (str): string to be printed in box"""
        self.draw_box(self.box4, action=['clear'])
        (x, y) = self.box4['origin']
        self.picaso.move_origin(x, y)
        self.picaso.put_string(string)

    def get_input(self, msg='>'):
        """Request an input from user in BOX4 with the message prompt 'msg'
        Input:
        msg (str): Prompt to be printed. User input will be printed on the next line"""
        
        string = ''
        (x, y) = self.box4['origin']
        self.picaso.move_origin(x, y)
        msg = msg  + '\n' + ' '*4
        self.picaso.put_string(msg)

        # Respond to key presses
        while True:
            try:
                key = numpad.key_pressed_queue.get(timeout=0.01)
            except Empty:
                continue

            self.picaso.move_origin(x, y)
            
            # Continue if NUMLOCK is deactivated
            if not numpad.led_on:#led_state_keypad(numpad):
                continue

            if key == ENTER:
                # Accept input
                self.draw_box(self.box4, action=['clear'])
                self.picaso.put_string('Last: ' + string)
                return string

            elif key == MINUS:
                # Add a 'minus'
                string += '-'
                self.draw_box(self.box4, action=['clear'])
                self.picaso.put_string(msg)
                self.picaso.put_string(string)

            elif key == PLUS:
                # Add a 'plus'
                string += '+'
                self.draw_box(self.box4, action=['clear'])
                self.picaso.put_string(msg)
                self.picaso.put_string(string)

            elif key == 'KEY_BACKSPACE':
                # delete last element
                string = string[:-1]
                self.draw_box(self.box4, action=['clear'])
                self.picaso.put_string(msg)
                self.picaso.put_string(string)

            elif key == 'KEY_KPSLASH':
                # Do nothing
                pass

            elif key == 'KEY_KPDOT':
                # Use english comma (dot)
                string += '.'
                self.draw_box(self.box4, action=['clear'])
                self.picaso.put_string(msg)
                self.picaso.put_string(string)

            elif key in KEY_NUM:
                # Add key to string
                string += key[-1]
                self.draw_box(self.box4, action=['clear'])
                self.picaso.put_string(msg)
                self.picaso.put_string(string)

            elif key == 'KEY_KPASTERISK':
                self.draw_box(self.box4, action=['clear'])
                return ''

    def main_screen(self):
        """Display main screen determined by set of attributes.
        """

        # Clear BOX4
        self.write_box4('')
        
        # Do nothing - info screen
        if self.locator == -1:
            self.write_box3()
            self.draw_box(self.box2, action=['clear'])
            (x, y) = self.box2['origin']
            self.picaso.move_origin(x, y)
            # Display helpful info
            self.picaso.put_string('Controls for the PREP manipulator\n')
            self.picaso.put_string('* : menu\n')
            self.picaso.put_string('/ : special functions or toggle\n')
            self.picaso.put_string('    between motors\n')
            self.picaso.put_string('<- : delete input character or\n')
            self.picaso.put_string('    go back one screen\n')
            self.picaso.put_string('NUMLOCK : Keypad locked if LED off\n')
            self.picaso.put_string('    or escapes motor motion.\n\n')
            self.picaso.put_string('Remember to give position to motors')
        # Main screen menu
        elif self.locator == 0:
            self.write_box3()
            self.draw_box(self.box2, action=['clear'])
            (x, y) = self.box2['origin']
            self.picaso.move_origin(x, y)
            self.picaso.put_string('1  - Incremental mode\n')
            self.picaso.put_string('2  - Absolute mode\n')
            self.picaso.put_string('3  - Change speed\n')
            self.picaso.put_string('\n')
            self.picaso.put_string('9  - Raster programs\n')
        # Inc MODE
        elif self.locator == 1 and self.sublocator == 1:
            self.incremental_mode()
        # Absolute MODE
        elif self.locator == 1 and self.sublocator == 2:
            self.absolute_mode()
        # Change speed menu
        elif self.locator == 1 and self.sublocator == 3:
            self.change_speed()
        # Raster programs
        elif self.locator == 1 and self.sublocator == 9:
            self.raster_programs()

    def incremental_mode(self):
        """Move a motor a step from its current position 
        SLASH: toggle between motor Z and Y.
        4 / 6: move cursor left/right to change order of magnitude (precision).
        2 / 8: change value down/up at selected precision.
        MINUS / PLUS: Set direction of value.
        ENTER: Make selected motor step the selected value.
        ASTERISK or BACKSPACE: Return to menu.
        NUMLOCK: breaks motion or locks keypad.
        """ 

        # Define needed variables
        sign = '+'
        values = [0, 1, 0, 0, 0]
        unit = 'mm'
        positions = {0: 1, # counter, index
                     1: 2,
                     2: 4,
                     3: 5,
                     4: 6}
        cursor = 1
        update_string = False

        # Assemble string
        inc = sign
        for i in values[0:2]: inc += str(i)
        inc += '.'
        for i in values[2:]: inc += str(i)
        inc += ' ' + unit
        
        self.draw_box(self.box2, action=['clear'])
        (x, y) = self.box2['origin']
        self.picaso.move_origin(x, y)
        self.picaso.put_string('Incremental mode')

        self.picaso.move_origin(x+5*self.char_height, y + 3*self.char_height)
        self.picaso.text_factor(2)
        self.picaso.put_string('Motor: ' + self.motor)

        self.picaso.move_origin(x+4*self.char_height, y + int(6.5*self.char_height))
        self.picaso.put_string(inc[:positions[cursor]])
        self.picaso.text_attribute('inverse', status=True)
        self.picaso.put_string(inc[positions[cursor]])
        self.picaso.text_attribute('inverse', status=False)
        self.picaso.put_string(inc[positions[cursor]+1:])

        # Respond to key presses
        while True:
            
            # Get new key
            try:
                key = numpad.key_pressed_queue.get(timeout=0.01)                    
            except Empty:
                continue
            
            # Continue if NUMLOCK is deactivated
            if not numpad.led_on:#led_state_keypad(numpad):
                continue

            # See menu
            elif key == 'KEY_KPASTERISK' or key == 'KEY_BACKSPACE':
                self.picaso.text_factor(1)
                self.locator = 0
                self.sublocator = 0
                self.main_screen()
                return

            # Accept string
            elif key == ENTER:
                print('Motor chosen: ' + self.motor)
                step = float(inc.split(' ')[0])
                print('to be stepped: {}'.format(step))
                if self.motor == 'Y':
                    orig_Y = inc
                    motor = Y
                elif self.motor == 'Z':
                    orig_Z = inc
                    motor = Z
                motor.increment(step)
                # display motion
                self.display_motion(motor)

            # Toggle between motors
            elif key == 'KEY_KPSLASH':
                if self.motor == 'Y':
                    self.motor = 'Z'
                    motor = Z
                elif self.motor == 'Z':
                    self.motor = 'Y'
                    motor = Y
                self.picaso.move_origin(x+5*self.char_height, y + 3*self.char_height)
                self.picaso.text_factor(2)
                self.picaso.put_string('Motor: ' + self.motor)
                self.picaso.text_factor(1)
                
            # Move cursor back and forth
            elif key == 'KEY_KP4':
                if cursor > 0:
                    cursor -= 1
                    update_string = True
            elif key == 'KEY_KP6':
                if cursor < 3:
                    cursor += 1
                    update_string = True

            # Change value according to position of cursor
            elif key == 'KEY_KP2':
                if values[cursor] > 0:
                    values[cursor] -= 1
                    update_string = True
                elif values[cursor] == 0:
                    values[cursor] = 9
                    update_string = True
            elif key == 'KEY_KP8':
                if values[cursor] < 9:
                    values[cursor] += 1
                    update_string = True
                elif values[cursor] == 9:
                    values[cursor] = 0
                    update_string = True

            # Change sign
            elif key == 'KEY_KPPLUS':
                if sign == '-':
                    sign = '+'
                    update_string = True
            elif key == 'KEY_KPMINUS':
                if sign == '+':
                    sign = '-'
                    update_string = True

            if update_string:
                # Assemble string and print it anew
                inc = sign
                for i in values[0:2]: inc += str(i)
                inc += '.'
                for i in values[2:]: inc += str(i)
                inc += ' ' + unit
                self.picaso.text_factor(2)
                self.picaso.move_origin(x+4*self.char_height, y + int(6.5*self.char_height))
                self.picaso.put_string(inc[:positions[cursor]])
                self.picaso.text_attribute('inverse', status=True)
                self.picaso.put_string(inc[positions[cursor]])
                self.picaso.text_attribute('inverse', status=False)
                self.picaso.put_string(inc[positions[cursor]+1:])
                self.picaso.text_factor(1)
                update_string = False

    def display_motion(self, motor):
        """Wait for motion to end while displaying motion and detecting a break """
        
        while motor.is_running():
            try:
                key = numpad.key_pressed_queue.get(timeout=0.01)
                if key == 'KEY_NUMLOCK':
                    motor.escape()
            except Empty:
                self.position[self.motor] = motor.get_position()
                self.write_box1(motion=True)
                
        else:
            self.position[self.motor] = motor.get_position()
            self.write_box1(motion=False)
                
    
    def format_absolute_string(self, string):
        """Convenience function for 'absolute_mode' to format the shown string """
        
        right = 3 # digits to the right of comma
        left = 3 # digits to the left of comma

        # Trim value string
        if len(string.split('.')[0]) < left:
            string = '0' + string
        length = len(string.split('.')[1])
        if length > right:
            string = string[:left + 1 + right + 1]
        elif length < right:
            diff = right - length
            string += '0'*diff
        string += ' mm'
        return string

    def update_absolute_string_from_values(self, values):
        """Convenience function for 'absolute_mode' to create the shown string from 'values' list """

        left, right = 3, 3
        string = ''
        for i in range(left): string += str(values[i])
        string += '.'
        for i in range(right): string += str(values[i+left])
        string += ' mm'
        return string

    def update_absolute_values_from_string(self, string):
        """Convenience function for 'absolute_mode' to create 'values' list from shown 'string' """

        values = []
        for i in string.split(' ')[0]:
            if i != '.':
                values.append(int(i))
        return values


    def absolute_mode(self):
        """Move a single motor to a given absolute value 
        SLASH: toggle between motor Z and Y.
        4 / 6: move cursor left/right to change order of magnitude (precision).
        2 / 8: change value down/up at selected precision.
        MINUS / PLUS: query user for new value in bottom display.
        ENTER: Make selected motor move to the selected value.
        ASTERISK or BACKSPACE: Return to menu.
        NUMLOCK: breaks motion or locks keypad.
        """
        
        # Define needed variables
        left, right = 3, 3
        orig_Y = self.format_absolute_string(str(Y.get_position()))
        orig_Z = self.format_absolute_string(str(Z.get_position()))
        if self.motor == 'Z':
            string = orig_Z
        elif self.motor == 'Y':
            string = orig_Y
        positions = {}
        for i in range(left):
            positions[i] = i
        for i in range(right):
            positions[i+left] = i + left + 1
        cursor = 0
        update_string = False
        
        # Assemble 'values'
        values = self.update_absolute_values_from_string(string)
        
        self.draw_box(self.box2, action=['clear'])
        (x, y) = self.box2['origin']
        self.picaso.move_origin(x, y)
        self.picaso.put_string('Absolute mode')

        self.picaso.move_origin(x+5*self.char_height, y + 3*self.char_height)
        self.picaso.text_factor(2)
        self.picaso.put_string('Motor: ' + self.motor)


        self.picaso.move_origin(x+4*self.char_height, y + int(6.5*self.char_height))
        self.picaso.put_string(string[:positions[cursor]])
        self.picaso.text_attribute('inverse', status=True)
        self.picaso.put_string(string[positions[cursor]])
        self.picaso.text_attribute('inverse', status=False)
        self.picaso.put_string(string[positions[cursor]+1:])

        # Respond to key press
        while True:
            try:
                key = numpad.key_pressed_queue.get(timeout=0.01)
            except Empty:
                continue
                
            # Continue if NUMLOCK is deactivated
            if not numpad.led_on:#led_state_keypad(numpad):
                continue

            # See menu
            elif key == 'KEY_KPASTERISK' or key == 'KEY_BACKSPACE':
                self.picaso.text_factor(1)
                self.locator = 0
                self.sublocator = 0
                self.main_screen()
                return

            # Accept string
            elif key == ENTER:
                print('Motor chosen: ' + self.motor)
                step = float(string.split(' ')[0])
                if self.motor == 'Y':
                    orig_Y = string
                    motor = Y
                elif self.motor == 'Z':
                    orig_Z = string
                    motor = Z
                motor.move(step)
                # display motion
                self.display_motion(motor)

            # Toggle between motors
            elif key == 'KEY_KPSLASH':
                if self.motor == 'Y':
                    self.motor = 'Z'
                    string = orig_Z
                elif self.motor == 'Z':
                    self.motor = 'Y'
                    string = orig_Y
                values = self.update_absolute_values_from_string(string)
                self.picaso.move_origin(x+5*self.char_height, y + 3*self.char_height)
                self.picaso.text_factor(2)
                self.picaso.put_string('Motor: ' + self.motor)
                self.picaso.text_factor(1)
                update_string = True

            # Move cursor back and forth
            elif key == 'KEY_KP4':
                if cursor > 0:
                    cursor -= 1
                    update_string = True
            elif key == 'KEY_KP6':
                if cursor < left + right - 1:
                    cursor += 1
                    update_string = True

            # Change value according to position of cursor
            elif key == 'KEY_KP2':
                if values[cursor] > 0:
                    values[cursor] -= 1
                    update_string = True
                elif values[cursor] == 0:
                    values[cursor] = 9
                    update_string = True
                string = self.update_absolute_string_from_values(values)
            elif key == 'KEY_KP8':
                if values[cursor] < 9:
                    values[cursor] += 1
                    update_string = True
                elif values[cursor] == 9:
                    values[cursor] = 0
                    update_string = True
                string = self.update_absolute_string_from_values(values)

            # Type new destination manually
            elif key == 'KEY_KPPLUS' or key == 'KEY_KPMINUS':
                self.picaso.text_factor(1)
                try:
                    string = self.format_absolute_string(str(float(self.get_input('Type destination:'))))
                except ValueError:
                    self.write_box4('Invalid input')
                    continue
                values = self.update_absolute_values_from_string(string)
                update_string = True

            # Reset with 'zero'
            elif key == 'KEY_KP0':
                if self.motor == 'Y':
                    string = orig_Y
                elif self.motor == 'Z':
                    string = orig_Z
                values = self.update_absolute_values_from_string(string)
                update_string = True
                    
            if update_string:
                # Assemble string and print it anew
                self.picaso.text_factor(2)
                self.picaso.move_origin(x+4*self.char_height, y + int(6.5*self.char_height))
                self.picaso.put_string(string[:positions[cursor]])
                self.picaso.text_attribute('inverse', status=True)
                self.picaso.put_string(string[positions[cursor]])
                self.picaso.text_attribute('inverse', status=False)
                self.picaso.put_string(string[positions[cursor]+1:])
                self.picaso.text_factor(1)
                update_string = False

            print(string)


        
    def change_speed(self):
        """Change the speed of both motors (mm/s) 
        ASTERISK or BACKSPACE: Return to menu.
        ENTER: Activate a query for new values. Enter new speed values for
        first Z motor and then Y motor as queried in bottom section.
        Enter an empty string or with unfloatable characters to abort.
        """

        # Clear box
        self.write_box3()
        self.draw_box(self.box2, action=['clear'])
        (x, y) = self.box2['origin']
        self.picaso.move_origin(x, y)
        self.picaso.put_string('Change speed\n\n')

        # Display current velocities
        self.picaso.put_string('Z speed: {} mm/s\n'.format(Z.get_running_velocity()))
        self.picaso.put_string('Y speed: {} mm/s\n'.format(Y.get_running_velocity()))

        # Respond to key press
        while True:
            try:
                key = numpad.key_pressed_queue.get(timeout=0.01)
            except Empty:
                continue

            # Continue if NUMLOCK is deactivated
            if not numpad.led_on:#led_state_keypad(numpad):
                continue

            # See menu
            elif key == 'KEY_KPASTERISK' or key == 'KEY_BACKSPACE':
                display.locator = 0
                display.sublocator = 0
                display.main_screen()
                return

            # If ENTER: Get speed input
            elif key == ENTER:
                try:
                    Z_speed = float(self.get_input('Type new speed for *Z* (mm/s)'))
                    time.sleep(0.5)
                except ValueError:
                    print('Illegal input. Returning from function.')
                    return

                try:
                    Y_speed = float(self.get_input('Type new speed for *Y* (mm/s)'))
                    time.sleep(0.5)
                except ValueError:
                    print('Illegal input. Returning from function.')
                    return

                # Set new speed
                response = Z.set_running_velocity(Z_speed)
                print(response)
                response = Y.set_running_velocity(Y_speed)
                print(response)
                print('Speed set to ({},{}) mm/s'.format(Z_speed, Y_speed))

                # Show new speed
                self.draw_box(self.box2, action=['clear'])
                (x, y) = self.box2['origin']
                self.picaso.move_origin(x, y)
                self.picaso.put_string('Change speed\n\n')

                # Display current velocities
                self.picaso.put_string('Z speed: {} mm/s\n'.format(Z.get_running_velocity()))
                self.picaso.put_string('Y speed: {} mm/s\n'.format(Y.get_running_velocity()))



    def raster_programs(self):
        """Choose a raster program from a list of raster pattern files
        Navigate list of files with '2' or '8'.
        Choose with 'ENTER'.
        Interrupt raster pattern with 'NUMLOCK'
        Go back to menu with 'ASTERISK' or 'BACKSPACE'
        """

        # Get available patterns from present working directory
        self.patterns = [x for x in os.listdir() if x.endswith('.pattern')]
        self.num_patterns = len(self.patterns)

        self.write_box3()
        self.draw_box(self.box2, action=['clear'])
        (x, y) = self.box2['origin']
        self.picaso.move_origin(x, y)

        # Check if patterns exist, else return
        if self.num_patterns == 0:
            self.picaso.put_string('\n\n   No ".pattern" files detected in folder!')
            time.sleep(2)
            self.locator = 0
            self.sublocator = 0
            self.main_screen()
            return

        last_counter = -1 # LAST_COUNTER to quickly update the new selection
        counter = 0 # COUNTER to navigate between files
        self.update_raster_list(counter, last_counter)
        
        while True:
            try:
                key = numpad.key_pressed_queue.get(timeout=0.01)
            except Empty:
                continue
            
            # Continue if NUMLOCK is deactivated
            if not numpad.led_on:#led_state_keypad(numpad):
                continue

            # See menu
            elif key == 'KEY_KPASTERISK' or key == 'KEY_BACKSPACE':
                display.locator = 0
                display.sublocator = 0
                display.main_screen()
                return

            # Pattern selected with ENTER
            elif key == ENTER:
                
                # Print chosen pattern file in BOX4
                print('File chosen: "{}"'.format(self.patterns[counter]))
                self.draw_box(self.box4, action=['clear'])
                (x, y) = self.box4['origin']
                self.picaso.move_origin(x, y)
                self.picaso.put_string('File chosen: "{}"'.format(self.patterns[counter]))

                # Clear BOX2
                self.draw_box(self.box2, action=['clear'])
                (x, y) = self.box2['origin']
                self.picaso.move_origin(x, y)
                
                # Start rastering...
                raster = ZY_raster_pattern(self.patterns[counter], Z=Z, Y=Y)
                raster.start()
                time.sleep(2)

                # Variables to track status and indicate motion of motors
                t0 = time.time()
                last_time = t0
                last_raster = raster.status
                motion_indicator = ''
                
                # Indicate running condition and allow for break
                while raster.status != 'Done':
                    try:
                        key = numpad.key_pressed_queue.get(timeout=0.1)

                    # Update motion indicator every few seconds
                    except Empty:
                        if time.time() - last_time > 2:
                            last_time = time.time()
                            if last_raster != raster.status:
                                last_raster = raster.status
                                motion_indicator = ''
                            else:
                                motion_indicator += '.'
                                if len(motion_indicator) > 3:
                                    motion_indicator = ''
                            self.draw_box(self.box2, action=['clear'])
                            (x, y) = self.box2['origin']
                            self.picaso.move_origin(x, y)
                            self.picaso.put_string(raster.status + motion_indicator)
                        continue

                    # Break if NUMLOCK
                    if key == 'KEY_NUMLOCK':
                        raster.stop()
                        while raster.status != 'Done':
                            self.draw_box(self.box2, action=['clear'])
                            (x, y) = self.box2['origin']
                            self.picaso.move_origin(x, y)
                            self.picaso.put_string(raster.status + '\nReturning to center...')
                            time.sleep(0.5)
                            empty_queue(numpad)
                        break

                # Indicate raster program is done
                self.draw_box(self.box2, action=['clear'])
                (x, y) = self.box2['origin']
                self.picaso.move_origin(x, y)
                self.picaso.put_string('Done!')

            # Move down in list
            elif key == 'KEY_KP2':
                if counter < self.num_patterns - 1:
                    last_counter = counter
                    counter += 1
                    self.update_raster_list(counter, last_counter)
                
            # Move up in list
            elif key == 'KEY_KP8':
                if counter > 0:
                    last_counter = counter
                    counter -= 1
                    self.update_raster_list(counter, last_counter)
                        


    def update_raster_list(self, counter, last_counter):
        """Convenience function to update list of raster programs on display """
        
        # Clear box and update origin
        (x, y) = self.box2['origin']
        self.picaso.move_origin(x, y)

        # Divide list into pages (sections)
        max_length = 7 # number of files listed per page
        sections = int(self.num_patterns/max_length) - 1
        rest = self.num_patterns%max_length
        if rest:
            sections += 1
        section = int((counter)/max_length)
        local_counter = counter%max_length
        last_local_counter = last_counter%max_length
        if last_counter == -1 or (local_counter == 0 and last_local_counter == max_length-1) or (last_local_counter == 0 and local_counter == max_length-1):
            self.draw_box(self.box2, action=['clear'])
            self.picaso.put_string('Raster programs:  ')
            self.picaso.put_string('Page {} of {}\n\n'.format(section+1, sections+1))

        # Limit number of files printed
        if section < sections:
            plus = max_length
        elif section == sections:
            if rest:
                plus = rest
            else:
                plus = max_length

        # Mark chosen file with INVERTED text
        full_range = range(section*max_length, section*max_length+plus)
        if last_counter == -1 or (local_counter == 0 and last_local_counter == max_length-1) or (last_local_counter == 0 and local_counter == max_length-1):
            for i in full_range:
                print(i, counter)
                if i == counter:
                    INVERT = True
                else:
                    INVERT = False
                self.picaso.text_attribute('inverse', status=INVERT)
                self.picaso.put_string(self.patterns[i] + '\n')
            if INVERT:
                self.picaso.text_attribute('inverse', status=False)
        else:
            self.picaso.move_origin(x, y + (2 + last_local_counter)*self.char_height)
            self.picaso.put_string('' + self.patterns[last_counter])
            self.picaso.move_origin(x, y + (2 + local_counter)*self.char_height)
            self.picaso.text_attribute('inverse', status=True)
            self.picaso.put_string('' + self.patterns[counter])
            self.picaso.text_attribute('inverse', status=False)

def led_state_keypad(numpad):
    """Get LED state of keypad's NUMLOCK
    Used to lock the keypad if NUMLOCK is off.
    """
    for (name, value) in numpad.device.leds(verbose=True):
        # Return true if LED is ON
        if name == 'LED_NUML':
            return True
    # Return false otherwise
    return False

def empty_queue(numpad):
    """Empty 'numpad' queue element
    In case a time.sleep() is used, a queue may inadvertently pile up.
    """
    
    while True:
        try:
            key = numpad.key_pressed_queue.get(timeout=0.1)
        except Empty:
            return


if __name__ == '__main__':

    # Connect to Z and Y motor
    Z, Y = connect_Z_Y()

    # Load display
    time.sleep(3)
    device = '/dev/serial/by-id/usb-FTDI_FT232R_USB_UART_A502BCBS-if00-port0'
    picaso = PicasouLCD28PTU(serial_device=device, baudrate=9600)
    spe_version = picaso.get_spe_version()
    picaso.screen_mode('landscape')
    if spe_version == '1.2':
        print('True version 1.2')
        picaso.clear_screen()
        picaso.move_cursor(0, 0)
    else:
        print('False ' + spe_version)
        sys.exit()
    display = TUI(picaso)
    
    # Load input stream
    np_path = detect_keypad_device()
    numpad = ThreadedKeypad(np_path)
    numpad.start()

    # Dictionaries
    KEY_SUBMENU = ['1', '2', '3', '9']
    ENTER = 'KEY_KPENTER'
    MINUS = 'KEY_KPMINUS'
    PLUS = 'KEY_KPPLUS'
    KEY_NUM = ['KEY_KP' + str(x) for x in range(10)]

    
    # Main loop
    t0 = time.time()
    while True:
        
        try:
            key = numpad.key_pressed_queue.get(timeout=0.01)
            display.last_key = ' '

            # Continue if NUMLOCK is deactivated
            if not numpad.led_on:#led_state_keypad(numpad):
                continue

            # See menu
            elif key == 'KEY_KPASTERISK':
                display.locator = 0
                display.sublocator = 0
                display.main_screen()

            # Go back with delete button
            elif key == 'KEY_BACKSPACE':
                if display.locator >= 0:
                    display.locator -= 1
                    if display.locator == -1:
                        display.sublocator = 0
                display.main_screen()

            # Numeral entered
            elif key in KEY_NUM:
                if display.locator == 0 and key[-1] in KEY_SUBMENU:
                    display.locator = 1
                    display.sublocator = int(key[-1])
                    display.main_screen()

            # Type special shortcuts
            elif key == 'KEY_KPSLASH':
                display.toggled['tog'] = True
                display.write_box3()
                user_string = display.get_input('Type a guess...')

                if display.locator == -1:
                    # Set electrical positions
                    if user_string == '123':
                        for i in ['Z', 'Y']:
                            if i == 'Z':
                                motor = Z
                            elif i == 'Y':
                                motor = Y
                            user_string = float(display.get_input('Set position {}:'.format(i)))
                            if user_string < motor.maxpos and user_string > motor.minpos:
                                motor.set_position(user_string)
                                display.position[i] = motor.get_position()
                                display.write_box1()
                            else:
                                display.picaso.put_string(' Out of range!')
                                time.sleep(1)
                                break
                    # Draw pikachu - simply because you can and have nothing better to do...
                    elif user_string == '9999':
                        continue # because we can't quite yet..
                        (x, y) = display.box2['origin']
                        feed_pikachu(picaso, origin=(x+30, y+20))
                display.toggled['tog'] = False
                
            # Update indicators
            display.write_box3()
            print(display.locator, display.sublocator)

        except Empty:
            continue
        except KeyboardInterrupt:
            numpad.stop()
            Z.stop()
            Y.stop()
            picaso.close()
            break
        except:
            numpad.stop()
            Z.stop()
            Y.stop()
            picaso.close()
            raise



        
    print('Exited normally')
