# pylint: disable=too-few-public-methods,no-member
"""File parser for Chemstation files

Copyright (C) 2015-2018 CINF team on GitHub: https://github.com/CINF

The General Stepped Program Runner is free software: you can
redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software
Foundation, either version 3 of the License, or
(at your option) any later version.

The General Stepped Program Runner is distributed in the hope
that it will be useful, but WITHOUT ANY WARRANTY; without even
the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more
details.

You should have received a copy of the GNU General Public License
along with The CINF Data Presentation Website.  If not, see
<http://www.gnu.org/licenses/>.

.. note:: This file parser went through a large re-write on ??? which
   changed the data structures of the resulting objects. This means
   that upon upgrading it *will* be necessary to update code. The
   re-write was done to fix some serious errors from the first
   version, like relying on the Report.TXT file for injections
   summaries. These are now fetched from the more ordered CSV files.

"""

from __future__ import print_function, unicode_literals, division

from collections import defaultdict
import codecs
import os
from itertools import islice
from io import BytesIO
import time
import struct
from struct import unpack

# The standard library csv module is no good for encoded CSV, which is
# kind of annoying
import unicodecsv as csv
import numpy

from PyExpLabSys.thirdparty.cached_property import cached_property
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


class NoInjections(Exception):
    """Exception raised when there are no injections in the sequence"""


class Sequence(object):
    """The Sequence class for the Chemstation data format

    Parameters:
        injections (list): List of :class:`~Injection`'s in this sequence
        sequence_dir_path (str): The path of this sequence directory
        metadata (dict): Dict of metadata
    """

    def __init__(self, sequence_dir_path):
        """Instantiate object properties

        Args:
            sequence_dir_path (str): The path of the sequence
        """
        self.injections = []
        self.sequence_dir_path = sequence_dir_path
        self.metadata = {}
        self._parse()
        if not self.injections:
            msg = 'No injections in sequence: {}'.format(self.sequence_dir_path)
            raise NoInjections(msg)
        self._parse_metadata()

    def _parse_metadata(self):
        """Parse metadata"""
        # Add metadata from first injection to sequence metadata
        first_injection = self.injections[0]
        self.metadata['sample_name'] = first_injection.metadata['sample_name']
        self.metadata['sequence_start'] = first_injection.metadata['injection_date']
        self.metadata['sequence_start_timestruct'] = \
            first_injection.metadata['injection_date_timestruct']
        self.metadata['acq_method'] = first_injection.metadata['acq_method']

    def _parse(self):
        """Parse the sequence"""
        sequence_dircontent = os.listdir(self.sequence_dir_path)
        # Put the injection folders in order
        sequence_dircontent.sort()
        for filename in sequence_dircontent:
            injection_fullpath = os.path.join(self.sequence_dir_path, filename)
            if not (filename.startswith("NV-") or filename.endswith(".D")):
                continue
            if not "Report.TXT" in os.listdir(injection_fullpath):
                continue
            self.injections.append(Injection(injection_fullpath))

    def __repr__(self):
        """Return Sequence object representation"""
        return "<Sequence object at {}>".format(self.sequence_dir_path)

    def full_sequence_dataset(self, column_names=None):
        """Generate peak name specific dataset

        This will collect area values for named peaks as a function of time over the
        different injections.

        Args:
            column_names (dict): A dict of the column names needed from the report lines.
                The dict should hold the keys: 'peak_name', 'retention_time' and 'area'.
                It defaults to: `column_names = {'peak_name': 'Compound Name',
                'retention_time': 'Retention Timemin', 'area': 'Area'}`

        Returns:
            dict: Mapping of signal_and_peak names and the values

        """
        # Set the column names default values
        if column_names is None:
            column_names = {
                'peak_name': 'Compound Name',
                'retention_time': 'Retention Time / min',
                'area': 'Area'
            }

        # Initialize the start time and data collection objects
        data = defaultdict(list)
        start_time = self.injections[0].metadata['injection_date_unixtime']

        # Loop over injections and collect data
        for injection in self.injections:
            elapsed_time = injection.metadata['injection_date_unixtime'] - start_time
            # Unknowns is used to sum up unknown values for a detector
            unknowns = defaultdict(float)

            # Loop over signal reports
            for signal, report in injection.reports.items():
                # Loop over report lines
                for report_line in report:
                    label = self._generate_label(data, signal, report_line, column_names)
                    # If it is a unknown peak, add the area
                    area = report_line[column_names['area']]
                    if label.endswith('?'):
                        unknowns[label] += area
                    else:
                        data[label].append([elapsed_time, area])

            # Add the summed unknown values for this injection
            for key, value in unknowns.items():
                data[key].append([elapsed_time, value])

        return dict(data)  # Convert the defaultdict back to dict

    @staticmethod
    def _generate_label(data, signal, report_line, column_names):
        """str: Return a label

        Args:
            data (dict): The data collected so far
            signal (str): The name of the signal
            report_line (dict): The current report line as a dict
            column_names (dict): column_names dict, see :meth:`~full_sequence_dataset`
        """
        # Base label e.g: "FID1 A  - CH4" or "TCD3 C  - ?"
        peak_name = report_line[column_names['peak_name']]
        label = '{} - {}'.format(signal, peak_name)
        if peak_name == '?':
            return label

        # Check whether we already have a label for this detector, molecule
        for existing_label in data:
            # Existing label is something like: "FID2 B  - CO2 (12.071)"
            # Extract the base label part from that
            existing_base_label = existing_label.split('(')[0].rstrip()
            if existing_base_label == label:
                return existing_label

        # For an known peak that we do not alread know about, add the retention time to
        # the label
        return '{} ({})'.format(label, report_line[column_names['retention_time']])


class Injection(object):
    """The Injection class for the Chemstation data format

    Parameters:
        injection_dirpath (str): The path of the directory of this injection
        reports (defaultdict): Signal -> list_of_report_lines dict. Each report line is
            dict of column headers to type converted column content. E.g::

             {u'Area': 22.81, u'Area %': 0.24, u'Height': 12.66,
              u'Peak Number': 1, u'Peak Type': u'BB', u'Peak Widthmin':
              0.027, u'Retention Timemin': 5.81}

            The columns headers are also stored in :attr`~metadata` under the `columns` key.
        reports_raw (defaultdict): Same as :attr:`~reports` except the content is not
            type converted.
        metadata (dict): Dict of metadata
        raw_files (dict): Mapping of ch_file_name -> :class:`~CHFile` objects
        report_txt (str or None): The content of the Report.TXT file from the
            injection folder is any

    """

    # This is scary. I don't know how many standard formats exist, or
    # if it is customizable !!!
    datetime_formats = (
        '%m/%d/%Y %I:%M:%S %p',  # '11/24/2017 12:11:42 PM'
        '%d-%b-%y %I:%M:%S %p',  # '24-Nov-17 12:10:07 PM'
        '%d-%b-%y, %H:%M:%S',  # '13-Jan-15, 11:16:49'
    )

    def __init__(self, injection_dirpath, load_raw_spectra=True, read_report_txt=True):
        """Instantiate Injection object

        Args:
            injection_dirpath (str): The path of the injection directory
            load_raw_spectra (bool): Whether to load raw spectra or not
            read_report_txt (bool): Whether to read and save the Report.TXT file
        """
        self.injection_dirpath = injection_dirpath
        self.reports = defaultdict(list)
        self.reports_raw = defaultdict(list)
        self.metadata = {}
        # Parse the Report00.CSV file
        self._parse_header()
        # Parse the table CSV files
        self._parse_tables()
        # Parse the raw files if requested
        self.raw_files = {}
        if load_raw_spectra:
            self._load_raw_spectra(injection_dirpath)
        # Read and save the Report.TXT file is requested
        self.report_txt = None
        if read_report_txt:
            report_path = os.path.join(self.injection_dirpath, 'Report.TXT')
            if os.path.isfile(report_path):
                with codecs.open(report_path, encoding='UTF16') as file_:
                    self.report_txt = file_.read()

    def _parse_date(self, date_part):
        """timestruct: Parse a date string in one of the formats in self.datetime_formats"""
        for datetime_format in self.datetime_formats:
            try:
                timestamp = time.strptime(date_part, datetime_format)
                break
            except ValueError:
                pass
        else:
            msg = "None of the date formats {} match the datestring {}"
            raise ValueError(msg.format(self.datetime_formats, date_part))
        return timestamp

    @staticmethod
    def _read_csv_data(filepath):
        """Return a list of rows from a csv file"""
        bytes_io = BytesIO()
        with codecs.open(filepath, encoding='UTF-16LE') as file_:
            content = file_.read()[1:]  # Get rid of the 2 byte order bytes
            bytes_io.write(content.encode('utf-8'))
        bytes_io.seek(0)

        csv_reader = csv.reader(bytes_io, encoding='utf-8')
        return list(csv_reader)

    def _add_value_unit_to_metadata(self, name, value, unit):
        """Add value or value / unit to metadata under name"""
        if unit.strip() != "":
            self.metadata[name] = value + ' / ' + unit
        else:
            self.metadata[name] = value

    def _parse_header(self):  # pylint: disable=too-many-branches
        """Parse injection metadata from the Report00.CSV file

        Extract information about: sample name, injection date and sequence start
        """
        csv_rows = self._read_csv_data(os.path.join(self.injection_dirpath, 'Report00.CSV'))

        # Convert names and types
        type_functions = {
            'number_of_signals': int, 'seq_line': int, 'inj': int,
            'number_of_columns': int,
        }
        for row in csv_rows:  # row is [name, value, other]
            name, value, _ = row
            name = name.strip().lower().replace('. ', '_').replace(' ', '_')
            row[0] = name
            if name in type_functions:
                row[1] = type_functions[name](value)

        # Parse first section of metadata
        row_iter = iter(csv_rows)  # Use an iterator to flexibly move through the 
        for row in row_iter:
            name, value, unit = row
            if name == 'number_of_signals':
                self.metadata[name] = value
                break

            self._add_value_unit_to_metadata(name, value, unit)
            if name in ("data_file", "analysis_method", "sequence_file"):
                self.metadata[name + '_filename'] = unit

        # Deal with signals
        self.metadata['signals'] = []
        for name, value, _ in islice(row_iter, self.metadata['number_of_signals']):
            self.metadata[name] = value
            self.metadata['signals'].append(value)

        # More metadata
        for row in row_iter:
            name, value, unit = row
            if name == 'number_of_columns':
                self.metadata[name] = value
                break
            self._add_value_unit_to_metadata(name, value, unit)

        # Deal with columns
        self.metadata['columns'] = []
        for name, value, unit in islice(row_iter, self.metadata['number_of_columns']):
            self._add_value_unit_to_metadata(name, value, unit)
            self.metadata[name] = self.metadata[name].strip()
            self.metadata['columns'].append(self.metadata[name])

        # Confirm that there are no more lines left
        try:
            next(row_iter)
        except StopIteration:
            pass
        else:
            raise RuntimeError('Still items left in metadata CSV')

        # Add a few extra fields for time structs
        for name in ("injection_date", "results_created"):
            if name in self.metadata:
                self.metadata[name + '_timestruct'] = self._parse_date(self.metadata[name])
                self.metadata[name + '_unixtime'] = time.mktime(
                    self.metadata[name + '_timestruct']
                )

    def _parse_tables(self):
        """Parse the report tables from CSV files"""
        # Guess types for columns
        types = {}
        for column_name in self.metadata['columns']:
            if 'peak number' in column_name.lower():
                types[column_name] = int
            elif 'peak type' in column_name.lower() or 'name' in column_name.lower():
                types[column_name] = str
            else:
                types[column_name] = float

        # Iterate over signals
        for signal_number in range(1, self.metadata['number_of_signals'] + 1):
            self._parse_table(signal_number, types)

    def _parse_table(self, signal_number, types):
        """Parse a single report table from a CSV file"""
        report_filename = 'REPORT{:0>2}.CSV'.format(signal_number)
        report_path = os.path.join(self.injection_dirpath, report_filename)
        csv_data = self._read_csv_data(report_path)
        signal = self.metadata['signal_{}'.format(signal_number)]
        for row in csv_data:
            row_dict = {}
            row_dict_raw = {}
            for column_name, value_str in zip(self.metadata['columns'], row):
                row_dict_raw[column_name] = value_str.strip()
                type_function = types[column_name]
                if type_function is str:
                    row_dict[column_name] = value_str.strip()
                else:
                    row_dict[column_name] = type_function(value_str)
            self.reports_raw[signal].append(row_dict_raw)
            self.reports[signal].append(row_dict)

    def _load_raw_spectra(self, injection_dirpath):
        """Load all the raw spectra (.ch-files) associated with this injection"""
        for file_ in os.listdir(injection_dirpath):
            if os.path.splitext(file_)[1] == '.ch':
                filepath = os.path.join(injection_dirpath, file_)
                self.raw_files[file_] = CHFile(filepath)

    def __repr__(self):
        """Return object representation"""
        return "<Injection object at {}>".format(self.injection_dirpath)


# Constants used for binary file parsing
ENDIAN = '>'
STRING = ENDIAN + '{}s'
UINT8 = ENDIAN + 'B'
UINT16 = ENDIAN + 'H'
INT16 = ENDIAN + 'h'
INT32 = ENDIAN + 'i'


def parse_utf16_string(file_, encoding='UTF16'):
    """Parse a pascal type UTF16 encoded string from a binary file object"""
    # First read the expected number of CHARACTERS
    string_length = unpack(UINT8, file_.read(1))[0]
    # Then read and decode
    parsed = unpack(STRING.format(2 * string_length),
                    file_.read(2 * string_length))
    return parsed[0].decode(encoding)


class CHFile(object):
    """Class that implementats the Agilent .ch file format version 179

    .. warning:: Not all aspects of the file header is understood, so there may and probably
       is information that is not parsed. See the method :meth:`._parse_header_status` for
       an overview of which parts of the header is understood.

    .. note:: Although the fundamental storage of the actual data has change, lots of
       inspiration for the parsing of the header has been drawn from the parser in the
       `ImportAgilent.m file <https://github.com/chemplexity/chromatography/blob/dev/
       Methods/Import/ImportAgilent.m>`_ in the `chemplexity/chromatography project
       <https://github.com/chemplexity/chromatography>`_ project. All credit for the parts
       of the header parsing that could be reused goes to the author of that project.

    Attributes:
        values (numpy.array): The internsity values (y-value) or the spectrum. The unit
            for the values is given in `metadata['units']`
        metadata (dict): The extracted metadata
        filepath (str): The filepath this object was loaded from

    """

    # Fields is a table of name, offset and type. Types 'x-time' and 'utf16' are specially
    # handled, the rest are format arguments for struct unpack
    fields = (
        ('sequence_line_or_injection', 252, UINT16),
        ('injection_or_sequence_line', 256, UINT16),
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
        """Instantiate object

        Args:
            filepath (str): The path of the data file
        """
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
        if version not in self.supported_versions:
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

        # Convert date
        self.metadata['datetime'] = time.strptime(self.metadata['date'], '%d-%b-%y, %H:%M:%S')

    def _parse_header_status(self):
        """Print known and unknown parts of the header"""
        file_ = open(self.filepath, 'rb')
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
                name, _, type_ = knowns[current_position]
                if type_ == 'x-time':
                    print('x-time, "{: <19}'.format(name + '"'),
                          unpack(ENDIAN + 'f', file_.read(4))[0] / 60000)
                elif type_ == 'utf16':
                    print(' utf16, "{: <19}'.format(name + '"'),
                          parse_utf16_string(file_))
                else:
                    size = struct.calcsize(type_)
                    print('{: >6}, "{: <19}'.format(type_, name + '"'),
                          unpack(type_, file_.read(size))[0])
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
                    # Only start a new collection of unknown bytes, if this byte is not a
                    # zero byte
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
        """The time values (x-value) for the data set in minutes"""
        return numpy.linspace(self.metadata['start_time'], self.metadata['end_time'],
                              len(self.values))
