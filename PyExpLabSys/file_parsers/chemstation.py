"""File parser for Chemstation files"""

from __future__ import print_function, unicode_literals, division
from collections import defaultdict

import codecs
import re
import os
import time
import math
import struct
from struct import unpack
from xml.etree import ElementTree

import numpy

from PyExpLabSys.thirdparty.cached_property import cached_property
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


# Constants used for binary file parsing
ENDIAN = '>'
STRING = ENDIAN + '{}s'
UINT8 = ENDIAN + 'B'
UINT16 = ENDIAN + 'H'
INT16 = ENDIAN + 'h'
INT32 = ENDIAN + 'i'


def parse_utf16_string(file_, encoding='UTF16'):
    """Parse a pascal type UTF16 encoded string from a binary file object"""
    string_length = unpack(UINT8, file_.read(1))[0]
    parsed = unpack(STRING.format(2 * string_length),
                    file_.read(2 * string_length))
    return parsed[0].decode(encoding)


class CHFile(object):
    """Class that implementats the Agilent .ch file format version 179

    .. note:: Not all aspects of the file header is understood, so there may and probably
       is information that is not parsed. See the method :meth:`._parse_header_status` for
       an overview of which parts of the header is understood.

    """

    # Fields is a table of name, offset and type. Types 'x-time' and 'utf16' are specially
    # handled, the rest are format arguments for struct unpack
    fields = (
        ('start_time', 282, 'x-time'),
        ('end_time', 286, 'x-time'),
        ('version_string', 326, 'utf16'),
        ('description', 347, 'utf16'),
        ('sample', 858, 'utf16'),
        ('operator', 1880, 'utf16'),
        ('date', 2391, 'utf16'),
        ('inlet', 2492, 'utf16'),
        ('instrument', 2533, 'utf16'),
        ('method', 2574, 'utf16'),
        ('software version', 3601, 'utf16'),
        ('software name', 3089, 'utf16'),
        ('software revision', 3802, 'utf16'),
        ('units', 4172, 'utf16'),
        ('detector', 4213, 'utf16'),
        ('yscaling', 4732, ENDIAN + 'd')
    )
    # The start position of the data
    data_start = 6144
    # The versions of the file format supported by this implementation
    supported_versions = {179}

    def __init__(self, filepath):
        self.filepath = filepath
        self.metadata = {}
        with open(self.filepath, 'rb') as file_:
            self._parse_header(file_)
            self.values = self._parse_data(file_)

    def _parse_header(self, file_):
        """Parse the header"""
        # Parse and check version
        length = unpack(UINT8, file_.read(1))[0]
        parsed = unpack(STRING.format(length), file_.read(length))
        version = int(parsed[0])
        if not version in self.supported_versions:
            raise ValueError('Unsupported file version {}'.format(version))
        self.metadata['magic_number_version'] = version

        # Parse all metadata fields
        for name, offset, type_ in self.fields:
            file_.seek(offset)
            if type_ == 'utf16':
                self.metadata[name] = parse_utf16_string(file_)
            elif type_ == 'x-time':
                self.metadata[name] = unpack(ENDIAN + 'f', file_.read(4))[0] / 60000
            else:
                self.metadata[name] = unpack(type_, file_.read(struct.calcsize(type_)))[0]

    def _parse_header_status(self):
        """Documents the state of how many bytes of the header is understood"""
        file_ = open(self.filepath, 'rb')

        print('Header parsing status')
        # Map positions to fields for all the known fields
        knowns = {item[1]: item for item in self.fields}
        # A couple of places has a \x01 byte before a string, these we simply skip
        skips = {325, 3600}
        # Jump to after the magic number version
        file_.seek(4)

        # Initialize variables for unknown bytes
        unknown_start = None
        unknown_bytes = b''
        # While we have not yet reached the data
        while file_.tell() < self.data_start:
            current_position = file_.tell()
            # Just continue on skip bytes
            if current_position in skips:
                file_.read(1)
                continue

            # If we know about a data field that starts at this point
            if current_position in knowns:
                # If we have collected unknown bytes, print them out and reset
                if unknown_bytes != b'':
                    print('Unknown at', unknown_start, repr(unknown_bytes.rstrip(b'\x00')))
                    unknown_bytes = b''
                    unknown_start = None

                # Print out the position, type, name and value of the known value
                print('Known field at {: >4},'.format(current_position), end=' ')
                name, position, type_ = knowns[current_position]
                if type_ == 'x-time':
                    print('x-time, "{: <19}'.format(name + '"'), unpack(ENDIAN + 'f', file_.read(4))[0] / 60000)
                elif type_ == 'utf16':
                    print(' utf16, "{: <19}'.format(name + '"'), parse_utf16_string(file_))
                else:
                    size = struct.calcsize(type_)
                    print('{: >6}, "{: <19}'.format(type_, name + '"'), unpack(type_, file_.read(size))[0])
            else:  # We do not know about a data field at this position If we have already
                # collected 4 zero bytes, assume that we are done with this unkonw field,
                # print and reset
                if unknown_bytes[-4:] == b'\x00\x00\x00\x00':
                    print('Unknown at', unknown_start, repr(unknown_bytes.rstrip(b'\x00')))
                    unknown_bytes = b''
                    unknown_start = None

                # Read one byte and save it
                one_byte = file_.read(1)
                if unknown_bytes == b'':
                    # Only start a new collection of unknown bytes, if this byte is not a zero byte
                    if one_byte != b'\x00':
                        unknown_bytes = one_byte
                        unknown_start = file_.tell() - 1
                else:
                    unknown_bytes += one_byte

        file_.close()

    def _parse_data(self, file_):
        """Parse the data"""
        # Go to the end of the file and calculate how many points 8 byte floats there are
        file_.seek(0, 2)
        n_points = (file_.tell() - self.data_start) // 8

        # Read the data into a numpy array
        file_.seek(self.data_start)
        return numpy.fromfile(file_, dtype='<d', count=n_points) * self.metadata['yscaling']

    @cached_property
    def times(self):
        """Return the time values for the data set (x-value)"""
        return numpy.linspace(self.metadata['start_time'], self.metadata['end_time'], len(self.values))
