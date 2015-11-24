"""File parser for Chemstation files"""

from __future__ import print_function

import codecs
import re

# Regular expressions quick guide
# () denotes a group that we want to capture
# [] denotes a group of characters to match
# * repeats the previous group if character
TABLE_RE = r'^ *([0-9]*) *([0-9\.]*)[A-Z ]*([0-9\.]*) *([0-9e\.]*) *([0-9e\.]*) *([a-zA-Z0-9\?]*)$'


class Report(object):
    """The Report class for the Chemstation data format"""

    def __init__(self, filepath):
        self.filepath = filepath
        self._parse_file()

    def _parse_file(self):
        """Parse a single Result.TXT file

        This file represents the results of a single injection

        MORE TO FOLLOW FIXME

        """
        # detector id and table open used during scanning of file
        detector = None
        table_open = False

        # Form the list of measurements by looking for tables and parsing tables lines
        self.measurements = []
        # File is UTF16 encoded
        with codecs.open(self.filepath, encoding='UTF16') as file_:
            for line in file_:
                if line.startswith('Totals :'):
                    # If line startswith Toals, the table has finished
                    table_open = False
                elif table_open:
                    # If the table is open, parse a table line
                    columns_dict = self._report_parse_line(line)
                    columns_dict['detector'] = detector
                    self.measurements.append(columns_dict)
                elif line.startswith('---'):
                    # If line starts with ---, then a table is about to start
                    table_open = True
                elif line.startswith('Signal'):
                    # If line starts with Signal, get the detector id
                    # Parse something like:
                    # Signal 2: FID2 B, Back Signal
                    # For a detector name
                    detector_part = line.split(': ')[1]
                    detector = detector_part.split(',')[0]

    @staticmethod
    def _report_parse_line(line):
        """Parse a single table line

        It looks like e.g:
        2  10.872         0.0000    0.00000  0.00000 CH4
        3  12.071         0.0000    0.00000  0.00000 CO2
        4  12.718 BB      0.4140  816.84735 1.000e2  ?
        """
        line = line.strip()
        # Making a regular expression search, returns a match object
        match = re.match(TABLE_RE, line)
        if match is None:
            print('PROBLEMS WITH THE REGULAR EXPRESSION')
        groups = match.groups()
        headers = ['Peak', 'a', 'b', 'c', 'd', 'e']  # Etc
        return dict(zip(headers, groups))
