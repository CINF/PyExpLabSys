"""File parser for Chemstation files"""

from __future__ import print_function, unicode_literals
from collections import defaultdict

import codecs
import re
import os
import time
import math
from xml.etree import ElementTree

from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


# Regular expressions quick guide
# () denotes a group that we want to capture
# [] denotes a group of characters to match
# * repeats the previous group if character
TABLE_RE = (r'^ *([0-9]*) *([0-9\.e-]*)([A-Z ]*)([0-9\.e-]*) *([0-9\.e-]*) *([0-9e\.]*) '
            r'*([a-zA-Z0-9\?]*)$')


class Sequence(object):
    """The Sequence class for the Chemstation data format"""

    def __init__(self, sequence_dir_path):
        self.injections = []
        self.sequence_dir_path = sequence_dir_path
        self.metadata = {}
        self._parse()
        if len(self.injections) == 0:
            raise ValueError('No injections in sequence: {}'.format(self.sequence_dir_path))
        self._parse_metadata()

    def _parse_metadata(self):
        """Parse metadata"""
        # Pull the method name out of the sequence.acaml file
        xml_file = ElementTree.parse(os.path.join(self.sequence_dir_path, 'sequence.acaml'))
        root = xml_file.getroot()
        method = root.findall('.//{urn:schemas-agilent-com:acaml15}Method')[0]
        method_name = method.find('{urn:schemas-agilent-com:acaml15}Name').text
        self.metadata['method_name'] = method_name

        # Add metadata from first injection to sequence metadata
        first_injection = self.injections[0]
        self.metadata['sample_name'] = first_injection.metadata['sample_name']
        self.metadata['sequence_start'] = first_injection.metadata['sequence_start']

    def _parse(self):
        """Parse the sequence"""
        sequence_dircontent = os.listdir(self.sequence_dir_path)
        # Put the injection folders in order
        sequence_dircontent.sort()
        for filename in sequence_dircontent:
            injection_fullpath = os.path.join(self.sequence_dir_path, filename)
            if not filename.startswith("NV-"):
                continue
            if not "Report.TXT" in os.listdir(injection_fullpath):
                continue
            self.injections.append(Injection(injection_fullpath))

    def __repr__(self):
        """Change of list name"""
        return "<Sequence object at {}>".format(self.sequence_dir_path)

    def full_sequence_dataset(self):
        """Generate molecule ('PeakName') specific dataset"""
        data = defaultdict(list)
        start_time = self.injections[0].metadata['unixtime']
        for injection in self.injections:
            elapsed_time = injection.metadata['unixtime'] - start_time
            for measurement in injection.measurements:
                label = self.generate_data_label(measurement)
                data[label].append([elapsed_time, measurement['Area']])
        return data

    @staticmethod
    def generate_data_label(measurement):
        """Return a label for a measurement

        For known molecule measurement gets detector-PeakName as label. For unnamed peaks
        label will be Unnamed and 0.01bin RetTime
        """
        if measurement['PeakName'] == '?':
            lower = math.floor(measurement['RetTime'] * 100.0) / 100.0
            upper = math.ceil(measurement['RetTime'] * 100.0) / 100.0
            return '{detector}  - ? {:.2f}-{:.2f}'.format(lower, upper, **measurement)
        else:
            # **measurement  turns into PeakName=..., detector=..., Type=...
            return '{detector}  - {PeakName}'.format(**measurement)


class Injection(object):
    """The Injection class for the Chemstation data format

    Params:
        measurements (list): List of measurement lines from the report
        metadata (dict): Dict of metadata
        report_filepath (str): The filepath of the report for the injection
    """

    def __init__(self, injection_dirpath):
        self.report_filepath = os.path.join(injection_dirpath, "Report.TXT")
        self.measurements = []
        self.metadata = {}
        self._parse_header()
        self._parse_file()

    def _parse_header(self):
        """Parse a header of Report.TXT file

        Extract information about: sample name, injection date and sequence start
        """
        with codecs.open(self.report_filepath, encoding='UTF16') as file_:
            for line in file_:
                if 'Area Percent Report' in line:
                    break
                elif line.startswith('Sample Name'):
                    sample_part = line.split(':')[1].strip()
                    self.metadata['sample_name'] = sample_part
                elif line.startswith('Injection Date'):
                    date_part = line.split(' : ')[1]
                    date_part = date_part.replace('Inj', '')
                    date_part = date_part.strip()
                    timestamp = time.strptime(date_part, '%d-%b-%y %I:%M:%S %p')
                    self.metadata['unixtime'] = time.mktime(timestamp)
                elif line.startswith('Last changed'):
                    if 'sequence_start' in self.metadata:
                        continue
                    date_part = line.split(' : ')[1]
                    date_part = date_part.split('by')[0].strip()
                    self.metadata['sequence_start'] = \
                        time.strptime(date_part, '%d-%b-%y %I:%M:%S %p')

    def _parse_file(self):
        """Parse a single Report.TXT file

        This file represents the results of a single injection
        """
        # detector id and table open used during scanning of file
        detector = None
        table_open = False

        # Form the list of measurements by looking for tables and parsing tables lines
        # File is UTF16 encoded
        with codecs.open(self.report_filepath, encoding='UTF16') as file_:
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

        Dictionary is returned where the keys are the headers:
        'Peak', 'RetTime', 'Type', 'Width', 'Area', 'Area%' , 'PeakName'
        """
        line = line.strip()
        # Making a regular expression search, returns a match object
        match = re.match(TABLE_RE, line)
        if match is None:
            print('PROBLEMS WITH REGULAR EXPRESSION PARSING OF THE FOLLOWING LINE')
            print(line)
        groups = match.groups()
        if len(groups) < 7:
            raise SystemExit()
        headers = ['Peak', 'RetTime', 'Type', 'Width', 'Area', 'Area%', 'PeakName']  # Etc
        content_dict = dict(zip(headers, groups))
        for header in content_dict.keys():
            if header in ['RetTime', 'Width', 'Area', 'Area%']:
                content_dict[header] = float(content_dict[header])
            elif header == 'Peak':
                content_dict[header] = int(content_dict[header])
            else:
                content_dict[header] = content_dict[header].strip()

        return content_dict
