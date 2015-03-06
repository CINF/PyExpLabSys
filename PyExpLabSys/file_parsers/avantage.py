# -*- coding: utf-8 -*-

"""Test module for Avantage files"""

from __future__ import division, unicode_literals, print_function

from pprint import pprint
import datetime
import codecs
import struct
import json
import os
import re
from collections import namedtuple
from io import BytesIO
from PyExpLabSys.thirdparty import olefile
from PyExpLabSys.thirdparty.cached_property import cached_property
olefile.KEEP_UNICODE_NAMES = True
import numpy as np

import logging
_LOG = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
_LOG.addHandler(logging.NullHandler())


# Named tuples
SP_AXES = namedtuple('SpaceAxes',
                     'num_points start step axis_type linear symbol unit label')
DA_AXES = namedtuple('DataAxes', 'start end numaxis unknown')

# Translation of space axes type numbers to type strings
SPACE_AXES_TYPES = {
    0: 'UNDEFINED',
    1: 'ENERGY',
    2: 'ANGLE',
    3: 'X',
    4: 'Y',
    5: 'LEVEL',
    6: 'ETCHLEVEL',
    10: 'POSITION',
    15: 'DISTANCE',
    16: 'RGB/COUNTS MIXED',
    17: 'PEAKS',
    20: 'PROFILE TYPE',
}

# Defaults for different axes types
SPACE_AXES_DEFAULTS = {
    'UNDEFINED': {'label': 'Undefined', 'symbol': '?', 'unit': '?'},  # 0
    'ENERGY': {'label': 'Energy', 'symbol': 'E', 'unit': 'eV'},  # 1
    'ANGLE': {'label': 'Angle', 'symbol': '\xd8', 'unit': '\xb0'},  # 2
    'X': {'label': 'X', 'symbol': 'X', 'unit': '\xb5m'},  # 3
    'Y': {'label': 'Y', 'symbol': 'Y', 'unit': '\xb5m'},  # 4
    'LEVEL': {'symbol': 'L', 'unit': ''},  # 5
    'ETCHLEVEL': {'label': 'Etch Level', 'symbol': 'EtchLevel', 'unit': ''},  # 6
    'POSITION': {'label': 'Position', 'symbol': 'Pos', 'unit': ''},  # 10
    'DISTANCE': {'label': 'Distance', 'symbol': 'd', 'unit': '\xb5m'},  # 15
    'RGB/COUNTS MIXED': {'symbol': 'RGB', 'unit': ''},  # 16
    'PEAKS': {'symbol': 'P'},  # 17
    'PROFILE TYPE': {'symbol': '', 'unit': ''},  # 20
    # Only found indirectly, so no type number
    'ETCHTIME': {'label': 'Etch Time', 'symbol': 'EtchTime', 'unit': 's'},
}


FIRST_CAP_RE = re.compile('(.)([A-Z][a-z]+)')
ALL_CAP_RE = re.compile('([a-z0-9])([A-Z])')
def camel_to_underscore(string):
    """ Convert camelcase to lowercase and underscore
    Recipy from http://stackoverflow.com/a/1176023
    """
    string = FIRST_CAP_RE.sub(r'\1_\2', string)
    return ALL_CAP_RE.sub(r'\1_\2', string).lower()


class UnexpectedStructure(Exception):
    """Exception used if a parse fails due to an unexpected structure"""
    pass


class UnableToParse(Exception):
    """Exception used if unable to parse a part"""
    pass


class NotXPSException(Exception):
    """Exception for trying to interpret non-XPS data as XPS data"""
    pass


class VGDFile(object):
    """Class that represents a Avatage data file (.VDG)"""

    def __init__(self, filepath, debug=False):
        self.filepath = filepath
        self.olefile = olefile.OleFileIO(
            filepath, raise_defects='DEFECT_INCORRECT', debug=debug
        )
        self._paths = {
            'summary_properties': '\x05SummaryInformation',
            'properties': '\x05Q5nw4m3lIjudbfwyAayojlptCa',
        }
        # Raw data seems to be stored as little endian 8 byte floats
        self.data_type = np.dtype('<f8')

    def __str__(self):
        """Returns the str representation for the file"""
        out = '<{}(filepath={})'.format(self.__class__.__name__, self.filepath)
        for component in self.list_components():
            out += '\n' + str(component)
        return out

    def list_components(self):
        """List components"""
        return self.olefile.listdir()

    @cached_property
    def summary_properties(self):
        """Returns the summary properties"""
        path = self._paths['summary_properties']
        return self.olefile.getproperties(path, convert_time=True)

    @cached_property
    def properties(self):
        """Return general properties"""
        path = self._paths['properties']
        properties = self.olefile.getproperties(path, convert_time=True)
        # Conver TXFN coefficient names
        if 'NumberOfTXFNCoeffs' in properties:
            for index in range(properties['NumberOfTXFNCoeffs']):
                properties['NumberOfTXFNCoeffs_{}'.format(index)] =\
                    properties.pop(100000 + index)
        return properties

    @cached_property
    def data(self):
        """Returns the data"""
        raw = self.olefile.openstream('VGData').read()
        # pylint: disable=no-member
        return np.fromstring(raw, dtype=numpy.float64)

    @property
    def supported_data(self):
        """Returns a boolean that confirms whether this data type is supported
        """
        support = {}
        for attr in ['space_axes', 'data_axes', 'data_back_markers',
                     'overlay_markers']:
            try:
                getattr(self, attr)
                support[attr] = True
            except UnableToParse:
                support[attr] = False
        return support

    @cached_property
    def space_axes(self):
        """Returns a list of space axes"""
        _LOG.debug("Space axes called")
        raw = self.olefile.openstream('VGSpaceAxes').read()
        raw_bio = BytesIO(raw)

        type_, num_axis, = struct.unpack('<2I', raw_bio.read(8))
        # It is unknown, what this type refers to
        if type_ != 131072:
            raise Exception('Unknown space axes data structure type {}'.format(type_))

        axes = []
        for n in range(num_axis):
            _LOG.debug("Parse space axis {}".format(n))
            axes.append(self._parse_single_space_axis(raw_bio))

        # For non linear axes, there is no type information, and so it has to
        # be inferred from one of the other axes
        types = [ax['type'] for ax in axes]
        if None in types:
            _LOG.debug('None in types')
            # If ETCHLEVEL is there, the type is ETCHTIME
            if 'ETCHLEVEL' in types:
                for ax in axes:
                    if ax['type'] is None:
                        ax['type'] = 'ETCHTIME'
                        self._update_space_axis_defaults(ax)   
            # Elif POSITION is there, types are X and Y
            elif 'POSITION' in types:
                position_types = ['Y', 'X']  # Popped from the end
                for axis in axes:
                    if axis['type'] is None:
                        axis['type'] = position_types.pop()
                        self._update_space_axis_defaults(axis)

        remainder = raw_bio.read()
        if len(remainder) != 0:
            raise Exception("Bad remainder")

        return axes

    def _parse_single_space_axis(self, raw_bio):
        """Parse a single space axis

        The structure of a single space is:
            label(bstr) + symbol(bstr) + unit(bstr) + points(I) + start(d) +
            width(d) + linear(b) (type(I) or non-lin-data)

        non-lin-data is the data steps for a non linear axis and consist of:
            points * number(d) + unknown(I)

        """
        axis = {}
        # First 3 bstrs, label, symbol, unit
        for name in ['label', 'symbol', 'unit']:
            chars, = struct.unpack('<I', raw_bio.read(4))
            bstr = raw_bio.read(chars)

            # If there is no string, don't add it to the dictionary
            if bstr == b'\x00\x00':
                continue

            # Decode the bstr as UTF-16 string
            axis[name] = bstr.decode('UTF-16LE')[:-1]

        # Read the 3 floats, points, start and width
        axis.update(dict(zip(
            ['points', 'start', 'width'],
            struct.unpack('<Idd', raw_bio.read(20))
        )))

        # Read whether the axis is linear and the type
        axis['linear'] = bool(struct.unpack('<b', raw_bio.read(1))[0])

        if axis['linear']:
            axis_type, = struct.unpack('<I', raw_bio.read(4))
            axis['type'] = SPACE_AXES_TYPES.get(axis_type)
            self._update_space_axis_defaults(axis)
        else:
            axis['type'] = None

        # Parse non-linear numbers, consisting of _points_ floats and 4 extra
        # bytes
        if not axis['linear']:
            # Read values
            values = struct.unpack('<{}d'.format(axis['points']),
                                   raw_bio.read(8 * (axis['points'])))
            raw_bio.read(4)

        return axis
        

    @staticmethod
    def _update_space_axis_defaults(axis):
        """Update space axis defaults"""
        for key, value in SPACE_AXES_DEFAULTS.get(axis['type'], {}).items():
            if key not in axis:
                axis[key] = value

    @cached_property
    def data_axes(self):
        """Returns a list of data axes"""
        raw = self.olefile.openstream('VGDataAxes').read()
        raw_bio = BytesIO(raw)
        type_, naxes = struct.unpack('<II', raw_bio.read(8))

        data_axes = []
        for _ in range(naxes):
            axis = struct.unpack('<4I', raw_bio.read(16))
            axis = dict(zip(['start', 'end', 'nspace', 'unknown'], axis))
            data_axes.append(axis)

        if len(raw_bio.read()) != 0:
            raise UnableToParse("Bad data axis length")

        return data_axes

    @cached_property
    def data_back_markers(self):
        """Data back marker"""
        raw = self.olefile.openstream('VGDataBackMarker').read()

        if len(raw) != 32:
            raise UnableToParse('Back Marker. Bad length')

        #space_axes = self.space_axes
        #if len(space_axes) != 1:
        #    raise UnableToParse("Data back marker, cannot read space axes")
        #print(space_axes[0])
        #end = space_axes[0].num_points

        parsed = struct.unpack('<8I', raw)

        #if parsed != (131072, 1, end, end, 1, end, 1, end):
        #    raise UnableToParse('Data back marker, bad parsing')
        return parsed

    @cached_property
    def overlay_markers(self):
        """Returns the overlay markers"""
        if ['VGOverlayMarkers'] in self.list_components():
            raw = self.olefile.openstream('VGOverlayMarkers').read()
            if raw != b'\x00\x00\x01\x00\x00\x00\x00\x00':
                raise UnableToParse("Overlay Markers")
            return raw
        else:
            return None


        # '\x00\x00\x01\x00\x00\x00\x00\x00'
        return raw

    @property
    def version(self):
        """Returns the version info bytes"""
        raw = self.olefile.openstream('VersionInfo').read()
        print('version', struct.unpack('<I', raw))
        return raw

    @cached_property
    def x(self):
        """Returns the x-axis data as kinetic energy"""
        if len(self.space_axes) != 1:
            raise UnableToParse("X axis data")
        axis = self.space_axes[0]

        if axis[3:] != ('ENERGY', 'LINEAR', 'E', 'eV', 'Energy'):
            raise UnableToParse("X axis data")

        print(axis)
        stop = axis.start + (axis.num_points - 1) * axis.step
        x, retstep = np.linspace(start=axis.start,
                                 stop=stop,
                                 num=axis.num_points,
                                 retstep=True)

        if not np.isclose(axis.step, retstep):
            raise UnableToParse("X axis, bad return step")

        return x

    @cached_property
    def x_be(self):
        """Returns the x-axis data as binding energy"""
        source_energy = self.properties.get('SourceEnergy')
        if self.properties.get('SourceType') is None:
            raise NotXPSException("No source energy found")

        return source_energy - self.x

    @cached_property
    def y(self):
        """Returns the y axis data FIXME unit"""
        if len(self.space_axes) != 1:
            raise UnableToParse("Y axis data")
        axis = self.space_axes[0]

        # Get the data stream
        data = self.olefile.openstream('VGData')
        points_size = self.data_type.itemsize * axis.num_points
        if data.size != points_size:
            raise UnableToParse("Y axis data, data stream size")

        return np.fromstring(data.read(points_size))


def avg_date(string):
    """ Parse a AVG date. It is on the form
    'DD/MM/YYYY   HH:MM:SS'
    without any padding of the day or month number but with zero padding of
    of the time elements.

    """
    return datetime.datetime.strptime(string, "%d/%m/%Y   %H:%M:%S")


def avg_str(string):
    """ Parse a AVG string """
    return string.strip("'")


def avg_bool(string):
    """ Return True if string is 'True' else False """
    return True if string == 'True' else False


class AVGFile(object):
    """ Class that read and represent a AVGFile """

    # Property line regular expression
    property_re = re.compile(r'^([A-Z_\[\]0-9]*) *: ([A-Z_0-9]*) *= (.*)$')

    # AVG types
    avg_types = {
        'VT_BSTR': avg_str,
        'VT_DATE': avg_date,
        'VT_I4': int,
        'VT_I2': int,
        'VT_R4': float,
        'VT_BOOL': avg_bool
    }

    def __init__(self, filepath):
        """ Read a AVG file """
        self.filepath = filepath
        self._file = codecs.open(filepath, encoding='latin-1')
        self._lines = (line.strip('\r\n') for line in self._file)

        self.axis = None
        self.data = None

    def _find_line(self, startswith):
        """Finds the line that startswith"""
        for line in self._lines:
            if line.startswith(startswith):
                return line

    @cached_property
    def file_format(self):
        """Returns the AVG file format number"""
        # The format line looks like this:
        #$FORMAT=4
        format_line = self._find_line("$FORMAT=")
        return int(line.split("=")[1])

    @cached_property
    def summary_properties(self):
        """Returns the summary properties"""
        self.file_format  # Parse format first
        self._find_line("$PROPERTIES=SUM")
        return self._parse_property_group()

    @cached_property
    def properties(self):
        """Returns the standard properties"""
        self.summary_properties  # Parse summary properties first
        self._find_line("$PROPERTIES=STD")
        return self._parse_property_group()

    def _parse_property_group(self):
        """Perses a property group"""
        properties = {}
        for line in self._lines:
            if line == '':
                break
            match = self.property_re.match(line)
            if match:
                groups = match.groups()
                data = self.avg_types[groups[1]](groups[2])
                properties[groups[0]] = data

        return properties


if __name__ == '__main__':
    main()
