# -*- coding: utf-8 -*-
"""
Driver for the Innova RT 6K UPS

Implemented from this document:
http://networkupstools.org/protocols/megatec.htmlL
"""

import serial
import io


#: The first 7 places of the response to the status inquiry are numbers, who
#: are paired with the names in the list below
STATUS_INQUIRY_NAMES = [
    'input_voltage',
    'input_fault_voltage',
    'output_voltage',
    'output_current_load_percent',
    'input_frequency',
    'battery_voltage',
    'temperature_C',
]
#: The last section of the response to the status inquiry are 0's and 1's,
#: which indicate the boolean status of the fields listed below.
STATUS_INQUIRY_BOOLEANS = [
    'utility_fail_immediate',
    'battery_low',
    'bypass_boost_or_buck_active',
    'UPS_failed',
    'UPS_type_is_standby',
    'test_in_progress',
    'shutdown_active',
    'beeper_on',
]
#: The names for the floats returned as section from the rating information
#: command
RATING_INFORMATION_FIELDS = [
    'rating_voltage',
    'rating_current',
    'battery_voltage',
    'frequency',
]


class Megatec(object):
    """Driver that implements parts of the Megatech specification"""

    def __init__(self, device, baudrate=2400, timeout=2.0):
        self.serial = serial.Serial(device, baudrate=baudrate, timeout=timeout)
        self.serialio = io.TextIOWrapper(
            io.BufferedRWPair(self.serial, self.serial),
            newline='\r'
        )
        print('init')

    def com(self, command):
        """Perform communication"""
        self.serialio.write(command)
        self.serialio.flush()
        return self.serialio.readline()

    def get_status(self):
        """Return the status as a dict

        The values in the dict are either float or booleans. The keys for the
        float values are:

         * output_voltage
         * input_voltage
         * temperature_C
         * input_frequency
         * battery_voltage
         * output_current_load_percent
         * input_fault_voltage

        The keys for the boolean values are:

         * utility_fail_immediate
         * battery_low
         * bypass_boost_or_buck_active
         * UPS_failed
         * UPS_type_is_standby
         * test_in_progress
         * shutdown_active
         * beeper_on

        """
        response = self.com('Q1\r')
        if response[0] != '(' or response[-1] != '\r':
            msg = ('Unexpect reply on status inquiry. Either did not start '
                   'with "(" or end with "\\r"')
            raise IOError(msg)

        # Split into section and
        sections = response.strip('(').split(' ')
        status = {name: float(value) for name, value in
                  zip(STATUS_INQUIRY_NAMES, sections)}

        # Section 7 are boolean indicators
        bool_strs = sections[7].strip()
        for name, bool_str in zip(STATUS_INQUIRY_BOOLEANS, bool_strs):
            status[name] = bool_str == '1'

        return status

    def test_for_10_sec(self):
        """Run a test of the batteries for 10 sec and return to utility"""
        response = self.com('T\r')
        if response.strip() != 'ACK':
            message = ('UPS response to command "T" was "{}", not "ACK" as '
                       'expected.')
            raise IOError(message.format(response))

    def ups_information(self):
        """Return the UPS information"""
        response = self.com('I\r')
        return response.strip()

    def ups_rating_information(self):
        """Return the UPS rating information as a dict

        The dict contains float valus for the following 4 fields:

         * battery_voltage
         * frequency
         * rating_current
         * rating_voltage
        """
        response = self.com('F\r')
        if response[0] != '#' or response[-1] != '\r':
            msg = ('Unexpect reply on status inquiry. Either did not start '
                   'with "#" or end with "\\r"')
            raise IOError(msg)            
        sections = response.strip('#\r').split(' ')

        rating_information = {}
        for name, value_str in zip(RATING_INFORMATION_FIELDS, sections):
            rating_information[name] = float(value_str)

        return rating_information


class InnovaRT6K(Megatec):
    """for the InnovaRT6k UPS"""


def main():
    from pprint import pprint
    innova = InnovaRT6K('COM1')
    #pprint(innova.get_status())
    pprint(innova.ups_rating_information())


if __name__ == '__main__':
    main()
