#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=too-few-public-methods,no-member

"""This file is used to parse XPS data from XML files from the SPECS
program.

In this file format the spectra (called regions) are containd in
so-called region groups inside the files. This structure is mirrored
in the data structure below.

NOTES:

Any is interpreted as being able to contain one item of different types.

"""

from __future__ import print_function

from xml.etree import ElementTree as ET
import logging
_LOG = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
_LOG.addHandler(logging.NullHandler())
import numpy as np


UNEXPECTED_TYPE_NAME = 'Unexpected XML element with type_name other than '\
                       '\'{}\' encountered'
UNHANDLED_XML_COMPONENTS = 'An unhandled XML component \'{}\' was found when '\
                           'parsing a \'{}\''
# Used in the conversion of elements with type information
XML_TYPES = {'string': str, 'ulong': long, 'double': float, 'boolean': bool}
ARRAY_TYPES = {'ulong': 'uint64', 'double': 'double'}
EXCEPTION_ON_UNHANDLED = True


def simple_convert(element):
    """Returns a simple XML structure consisting only of structs,
    sequences and simple types to dicts, lists and simple Python types.

    FIXME. More explanation.
    """

    # parse no content
    if element.text is None:
        out = None
    # parse array
    elif '\n' in element.text and element.tag in ARRAY_TYPES.keys():
        out = np.fromstring(element.text, dtype=ARRAY_TYPES[element.tag],
                            sep='\n')
    # parse simple type
    elif element.tag in XML_TYPES.keys():
        out = XML_TYPES[element.tag](element.text)
    # parse struct
    elif element.tag == 'struct':
        out = {e.attrib['name']: simple_convert(e) for e in element}
    # parse sequence
    elif element.tag == 'sequence':
        out = [simple_convert(e) for e in element]
    # parse any
    elif element.tag == 'any':
        if len(element) == 0:
            out = None
        elif len(element) == 1:
            out = simple_convert(element[0])
        else:
            raise ValueError(
                'Unexpected number of \'any\' children {}'.format(len(element))
            )
    # parse enum
    elif element.tag == 'enum':
        out = element.text
    # I don't know what to do
    else:
        raise ValueError('Unknown tag type {}'.format(element.tag))

    return out


class SpecsFile(list):
    """This is the top structure for a parsed file. It contais a list of
    RegionGroups

    The class contains a 'filepath' and 'region_group_sequences' attributes.

    """

    def __init__(self, filepath):
        """Parse the XML and initialize the internal variables"""
        super(SpecsFile, self).__init__()
        self.filepath = filepath
        root = ET.parse(filepath).getroot()

        _reg_group_seq = root.find('sequence[@type_name=\'RegionGroupSeq\']')
        for element in _reg_group_seq.findall(
                'struct[@type_name=\'RegionGroup\']'):
            _LOG.debug('Found region group: {}'.format(element))
            self.append(RegionGroup(element))
            _reg_group_seq.remove(element)

        # Check that there are no unhandled XML elements left in the region
        # group sequence
        if len(_reg_group_seq) > 0:
            message = UNHANDLED_XML_COMPONENTS.format(
                _reg_group_seq[0], 'region group sequence'
            )
            if EXCEPTION_ON_UNHANDLED:
                raise ValueError(message)
            else:
                _LOG.warning(message)
        root.remove(_reg_group_seq)

        # Check that there are no unhandled XML elements in the root
        if len(root) > 0:
            message = UNHANDLED_XML_COMPONENTS.format(
                root[0], 'file'
            )
            if EXCEPTION_ON_UNHANDLED:
                raise ValueError(message)
            else:
                _LOG.warning(message)

    def search_regions(self, search_term, case_insensitive=False):
        """Returns an iterator of search results for regions by name"""
        if case_insensitive:
            search_term = search_term.lower()
        for region_group in self:
            for region in region_group:
                if case_insensitive:
                    name = region.name.lower()
                else:
                    name = region.name
                if search_term in name:
                    yield region

    def __repr__(self):
        """Returns class representation"""
        return '<{}(filename=\'{}\')>'.format(self.__class__.__name__,
                                              self.filepath)

    def __str__(self):
        """Returns str representation"""
        out = self.__repr__()
        for region_group in self:
            for line in region_group.__str__().split('\n'):
                out += '\n    ' + line
        return out


class RegionGroup(list):
    """ Class that represents a region group

    The class contains a 'name', 'regions' and 'parameters' attribute.

    """

    def __init__(self, xml):
        """Initializes the region group

        Expects to find 3 subelement; the name, regions and
        parameters. Anything else raises an exception.

        Parsing parameters is not supported and therefore logs a
        warning if there are any.

        """
        super(RegionGroup, self).__init__()

        # Get name, find a string tag with attribute 'name' with value 'name'
        self.name = xml.findtext('string[@name=\'name\']')
        xml.remove(xml.find('string[@name=\'name\']'))

        _region_data_seq = xml.find('sequence[@type_name=\'RegionDataSeq\']')
        for element in _region_data_seq.findall(
                'struct[@type_name=\'RegionData\']'):
            _LOG.debug('Found region: {}'.format(element))
            self.append(Region(element))
            _region_data_seq.remove(element)
        # Check that there we nothing else than regions in the region data
        # sequence
        if len(_region_data_seq) > 0:
            message = UNHANDLED_XML_COMPONENTS.format(
                _region_data_seq[0], 'region data sequence in region group'
            )
            if EXCEPTION_ON_UNHANDLED:
                raise ValueError(message)
            else:
                _LOG.warning(message)
        xml.remove(_region_data_seq)

        # Parse parameters
        _params = xml.find('sequence[@type_name=\'ParameterSeq\']')
        self.parameters = simple_convert(_params)
        xml.remove(_params)

        # Check if there are any unhandled XML components
        if len(xml) > 0:
            message = UNHANDLED_XML_COMPONENTS.format(
                xml[0], 'region group'
            )
            if EXCEPTION_ON_UNHANDLED:
                raise ValueError(message)
            else:
                _LOG.warning(message)

    def __repr__(self):
        """Returns class representation"""
        return '<{}(name=\'{}\')>'.format(self.__class__.__name__, self.name)

    def __str__(self):
        """Return the class str representation"""
        out = self.__repr__()
        for region in self:
            out += '\n    ' + region.__str__()
        return out


class Region(object):
    """Class that represents a region

    The class contains attributes for the items listed in the
    'information_names' class variable.

    All auxiliary information is also available from the 'info' attribute.

    """

    information_names = ['name', 'region', 'mcd_head', 'mcd_tail',
                         'analyzer_info', 'source_info', 'remote_info',
                         'cycles', 'compact_cycles', 'transmission',
                         'parameters']

    def __init__(self, xml, cache_calculated=True):
        """Parse the XML and initialize internal variables"""
        # Internal variables
        self.cache_calculated = cache_calculated
        self._data = {}

        # Parse information items
        self.info = {}
        for name in self.information_names:
            element = xml.find('*[@name=\'{}\']'.format(name))
            self.info[name] = simple_convert(element)
            # Dynamically create attributes for all the items
            setattr(self, name, self.info[name])
            xml.remove(element)

        # Check if there are any unhandled XML components
        if len(xml) > 0:
            message = UNHANDLED_XML_COMPONENTS.format(
                xml[0], 'region group'
            )
            if EXCEPTION_ON_UNHANDLED:
                raise ValueError(message)
            else:
                _LOG.warning(message)

    def __repr__(self):
        """Returns class representation"""
        return '<{}(name=\'{}\')>'.format(
            self.__class__.__name__, self.name,
            )

    @property
    def x(self):  # pylint: disable=invalid-name
        """Returns the kinetic energy x-values"""
        if 'x' in self._data:
            # Return cached values
            data = self._data['x']
        else:
            # Calculate the x-values
            start = self.region['kinetic_energy']
            end = start + (self.region['values_per_curve'] - 1) *\
                  self.region['scan_delta']
            data = np.linspace(start, end, self.region['values_per_curve'])
            _LOG.debug('Creating x values from {} to {} in {} steps'.format(
                start, end, self.region['values_per_curve']))
            # Possibly cache the calculated values
            if self.cache_calculated:
                self._data['x'] = data

        return data

    @property
    def x_be(self):
        """Returns the binding energy x-values"""
        if self.region['analysis_method'] != 'XPS':
            message = "Analysis_method is {}".format(
                self.region['analysis_method'])
            raise NotXPSException(message)

        if 'x_be' in self._data:
            # Return cached value
            data = self._data['x_be']
        else:
            # Calculate the x binding energy values
            data = self.region['excitation_energy'] - self.x
            _LOG.debug('Creating x_be values from {} to {} in {} steps'.format(
                data.min(), data.max(),
                data.size))
            # Possibly cache the result
            if self.cache_calculated:
                self._data['x_be'] = data

        return data

    @property
    def iter_cycles(self):
        """Returns an iterable of cycles containing only theirs scans"""
        for cycle in self.cycles:
            yield (scan['counts'] for scan in cycle['scans'])

    @property
    def iter_scans(self):
        """Returns an iterator of scans"""
        for cycle in self.iter_cycles:
            for scan in cycle:
                yield scan

    @property
    def y_avg_counts(self):
        """Returns the average counts"""
        if 'y_avg_counts' in self._data:
            # Return cached result
            data = self._data['y_avg_counts']
        else:
            # Calculate the average counts
            vstack = np.vstack(scan for scan in self.iter_scans)
            data = vstack.mean(axis=0)
            _LOG.debug('Creating {} y_avg values from {} scans'.format(
                data.size, vstack.shape[0]
            ))
            # Possibly cache the result
            if self.cache_calculated:
                self._data['y_avg_counts'] = data

        return self._data['y_avg_counts']

    @property
    def y_avg_cps(self):
        """Returns the average counts per second"""
        if 'y_avg_cps' in self._data:
            data = self._data['y_avg_cps']
        else:
            data = self.y_avg_counts / self.region['dwell_time']
            _LOG.debug('Creating {} y_avg values'.format(data.size))
            if self.cache_calculated:
                self._data['y_avg_cps'] = data

        return data


class NotXPSException(Exception):
    """Exception for trying to interpret non-XPS data as XPS data"""
    pass
