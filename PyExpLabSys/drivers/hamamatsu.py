""" This is a driver for the Hamamatsu LC-L1V5 LED Driver. It is based on the Users's Manual for LC-L1V5 version W2-0363-5 """

from __future__ import print_function
import time
import logging
import serial
from PyExpLabSys.common.supported_versions import python2_and_3

# Configure logger as library logger and set supported python versions
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)


class LCL1V5:
    """ Driver for the Hamamatsu LC-L1V5 LED Driver """

    def __init__(self, port="/dev/ttyUSB0"):
        """ Open the serial port """
        self.ser = serial.Serial(port)
        time.sleep(0.1)

    def comm(self, command):
        """ Handle sending and receiving commands """
        self.ser.write((command + '\r').encode('ascii'))
        time.sleep(0.1)
        return_string = self.ser.read(self.ser.inWaiting()).decode()
        print(return_string)
        return return_string

    def select_command_communication(self):
        """Selecting command communication opens for sending commands to the controller via the serial interface.
        in panel control mode the commands are limited to checking the control mode"""

        command = 'CNT1'
        response = self.comm(command)
        return response

    def check_control_mode(self):
        """Check control mode
        CNT0: Panel control
        CNT1: Command communication
        """

        command = 'CNTQ'
        response = self.comm(command)
        return response

    def switch_led_on(self, channel):
        """select a led to switch on.

        Parameters
        ----------
        channel : int
            {0 : 'switch on all leds',
             1 : 'switch on led 1',
             2 : 'switch on led 2',
             3 : 'switch on led 3',
             4 : 'switch on led 4'}
        """

        command = 'ON' + str(channel)
        response = self.comm(command)
        return response

    def switch_led_off(self, channel):
        """select a led to switch off.

        Parameters
        ----------
        channel : int
            {0 : 'switch off all leds',
             1 : 'switch off led 1',
             2 : 'switch off led 2',
             3 : 'switch off led 3',
             4 : 'switch off led 4'}
        """
        command = 'OFF' + str(channel)
        response = self.comm(command)
        return response

    def check_led_status(self, channel):
        """Check the status of a led. For information about steps, refer to manual page 28

        Parameters
        ----------
        channel : int

        Return
        ---------
        channel, step

        step : {0 : 'off',
                1 : 'step 1',
                2 : 'step 2',
                3 : 'step 3'}
        """
        command = 'STPQ' + str(channel)
        response = self.comm(command)

        return response

    def set_step_settings(self, channel, intensities, times):
        """Sets the intensity and time for all 3 steps on selected channel

        Parameters
        ----------
        channel : int

        intensities (%) : str
           range : 000 - 100

        times (s) : str
           range : 00 - 99
           * if times < 10 s
           range : 0.1 - 9.9
        ---------

        Example
        --------
        set_step_settings(1,('010','050','100'),('5.0','10','99'))

        """

        command = 'CURE' + str(channel)
        stop_sign = 'STOP'
        # The tuples must contain 3 steps
        if len(intensities) != 3:
            print("intensities has to contain intensities of all 3 steps")
        elif len(times) != 3:
            print("intensities has to contain intensities of all 3 steps")
        else:
            print('')

        # check if the items are strings
        for i in range(3):
            if not isinstance(intensities[i], str) or len(intensities[i]) != 3:
                print('Intensities must be given as strings with 3 characters')
                command += stop_sign
            else:
                command += ',' + intensities[i]

            if not isinstance(times[i], str):
                print('Times must be a tuple of strings')
                command += stop_sign
            else:
                command += ',' + times[i]

        if stop_sign in command:
            print('something went wrong with the command')
            response = stop_sign
        else:
            print(command)
            response = self.comm(command)
        return response

    def start_stepped_program(self, channel):
        """start the programmed irradiation set with set_step_settings"""

        command = 'START' + str(channel)
        response = self.comm(command)

        return response


if __name__ == '__main__':

    # Initialize the driver
    LED = LCL1V5()

    time.sleep(0.5)
    # Turn on external communication
    LED.select_command_communication()
