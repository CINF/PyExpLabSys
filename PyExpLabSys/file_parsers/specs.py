#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=too-few-public-methods,no-member

"""This file is used to parse XPS and ISS data from XML files from the
SPECS program.

In this file format the spectra (called regions) are containd in
region groups inside the files. This structure is mirrored in the data
structure below where classes are provided for the 3 top level objects:

Files -> Region Groups -> Regions

The parser is strict, in the sense that it will throw an exception if
it encounters anything it does not understand. To change this behavior
set the EXCEPTION_ON_UNHANDLED module variable to False.

Usage examples
^^^^^^^^^^^^^^

To use the file parse, simply feed the top level data structure a path
to a data file and start to use it:

.. code-block:: python

 from PyExpLabSys.file_parsers.specs import SpecsFile
 import matplotlib.pyplot as plt

 file_ = SpecsFile('path_to_my_xps_file.xml')
 # Access the regions groups by iteration
 for region_group in file_:
     print '{} regions groups in region group: {}'.format(
         len(region_group), region_group.name)

 # or by index
 region_group = file_[0]

 # And again access regions by iteration
 for region in region_group:
     print 'region: {}'.format(region.name)

 # or by index
 region = region_group[0]

 # or you can search for them from the file level
 region = list(file_.search_regions('Mo'))[0]
 print region
 # NOTE the search_regions method returns a generator of results, hence the
 # conversion to list and subsequent indexing

 # From the regions, the x data can be accessed either as kinetic
 # or binding energy (for XPS only) and the y data can be accessed
 # as averages of the counts, either as pure count numbers or as
 # counts per second. These options works independently of each
 # other.

 # counts as function of kinetic energy
 plt.plot(region.x, region.y_avg_counts)
 plt.show()

 # cps as function of binding energy
 plt.plot(region.x_be, region.y_avg_cps)
 plt.show()

 # Files also have a useful str representation that shows the hierachi
 print file_

NOTES
^^^^^

The file format seems to basically be a dump, of a large low level
data structure from the implementation language. With an appropriate
mapping of low level data structure types to python types (see details
below and in the simple_convert function), this data structure could have been
mapped in its entirety to python types, but in order to provide a more
clear data structure a more object oriented approach has been taken,
where the top most level data structures are implemented as
classes. Inside of these classes, the data is parsed into numpy arrays
and the remaining low level data structures are parsed in python data
structures with the simple_convert function.

Module Documentation
^^^^^^^^^^^^^^^^^^^^

"""

from __future__ import print_function

from xml.etree import ElementTree as ET
import codecs
import logging
_LOG = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
_LOG.addHandler(logging.NullHandler())
import numpy as np
import six
from PyExpLabSys.thirdparty.cached_property import cached_property
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

if six.PY3:
    long = int


UNHANDLED_XML_COMPONENTS = 'An unhandled XML component \'{}\' was found when '\
                           'parsing a \'{}\''
# Used in the conversion of elements with type information
XML_TYPES = {
    'string': six.text_type, 'ulong': long, 'double': float, 'boolean': bool,
    'long': long,
}
ARRAY_TYPES = {'ulong': 'uint64', 'double': 'double'}
EXCEPTION_ON_UNHANDLED = True


def simple_convert(element):
    """Converts a XML data structure to pure python types.

    Args:
        element (xml.etree.ElementTree.Element): The XML element to convert

    Returns:
        object: A hierachi of python data structure

    Simple element types are converted as follows:

    +------------------------+
    | XML type | Python type |
    +==========+=============+
    | string   | str         |
    +----------+-------------+
    | ulong    | long        |
    +----------+-------------+
    | double   | float       |
    +----------+-------------+
    | boolean  | bool        |
    +----------+-------------+
    | struct   | dict        |
    +----------+-------------+
    | sequence | list        |
    +----------+-------------+

    Arrays are converted to numpy arrays, wherein the type conversion is:

    +-------------------------+
    | XML type | Python type  |
    +==========+==============+
    | ulong    | numpy.uint64 |
    +----------+--------------+
    | double   | numpy.double |
    +----------+--------------+

    Besides these types there are a few special elements that have a
    custom conversion.

    * **Enum** are simply converted into their value, since enums are
      considered to be a program implementation detail whose
      information is not relavant for a data file parser
    * **Any** is skipped and replaced with its content

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
        message = 'Unknown tag type {} with value:\n{}'.format(
            element.tag, element.text)
        if EXCEPTION_ON_UNHANDLED:
            raise ValueError(message)
        _LOG.warning(message)

    return out


class SpecsFile(list):
    """This is the top structure for a parsed file which represents a list
    of RegionGroups

    The class contains a 'filepath' attribute.

    """

    def __init__(self, filepath, encoding=None):
        """Parse the XML and initialize the internal variables"""
        super(SpecsFile, self).__init__()
        self.filepath = filepath
        if encoding:
            file_ = codecs.open(filepath, mode='r', encoding=encoding)
            content = file_.read()
            root = ET.fromstring(content.encode('utf-8'))
        else:
            try:
                root = ET.parse(filepath).getroot()
            except ET.ParseError as exception:
                print('#####\nParsing of the XML file failed. Possibly the '
                      'XML is mal-formed or you need to supply the encoding '
                      'of the XML file.\n\n###Traceback:')
                raise

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
            _LOG.warning(message)
        root.remove(_reg_group_seq)

        # Check that there are no unhandled XML elements in the root
        if len(root) > 0:
            message = UNHANDLED_XML_COMPONENTS.format(
                root[0], 'file'
            )
            if EXCEPTION_ON_UNHANDLED:
                raise ValueError(message)
            _LOG.warning(message)

    @property
    def regions_iter(self):
        """Returns a iteration over the regions"""
        for region_group in self:
            for region in region_group:
                yield region

    def search_regions_iter(self, search_term):
        """Returns an generator of search results for regions by name

        Args:
            search_term (str): The term to search for (case sensitively)

        Returns:
            generator: An iterator of maching regions

        """
        for region in self.regions_iter:
            if search_term in region.name:
                yield region

    def search_regions(self, search_term):
        """Returns an list of search results for regions by name

        Args:
            search_term (str): The term to search for (case sensitively)

        Returns:
            list: A list of matching regions

        """
        return list(self.search_regions_iter(search_term))

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

    @property
    def unix_timestamp(self):
        """Returns the unix timestamp of the first region"""
        for region_group in self:
            for region in region_group:
                if region.unix_timestamp is not None:
                    return region.unix_timestamp

    def get_analysis_method(self):
        """Returns the analysis method of the file

        Raises:
            ValueError: If more than one analysis method is used
        """
        methods = set()
        for region in self.regions_iter:
            methods.add(region.region['analysis_method'])

        if len(methods) > 1:
            message = 'More than one analysis methods is used inside this file'
            raise ValueError(message)

        return methods.pop()


class RegionGroup(list):
    """Class that represents a region group, which consist of a list of
    regions

    The class contains a 'name' and and 'parameters' attribute.

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

    Some useful ones are:
     * **name**: The name of the region
     * **region**: Contains information like, dwell_time, analysis_method,
       scan_delta, excitation_energy etc.

    All auxiliary information is also available from the 'info'
    attribute.

    """

    information_names = ['name', 'region', 'mcd_head', 'mcd_tail',
                         'analyzer_info', 'source_info', 'remote_info',
                         'cycles', 'compact_cycles', 'transmission',
                         'parameters']

    def __init__(self, xml):
        """Parse the XML and initialize internal variables

        Args:
            xml (xml.etree.ElementTree.Element): The region XML element

        """
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

    @cached_property
    def x(self):  # pylint: disable=invalid-name
        """Returns the kinetic energy x-values as a Numpy array"""
        # Calculate the x-values
        start = self.region['kinetic_energy']
        end = start + (self.region['values_per_curve'] - 1) *\
              self.region['scan_delta']
        data = np.linspace(start, end, self.region['values_per_curve'])
        _LOG.debug('Creating x values from {} to {} in {} steps'.format(
            start, end, self.region['values_per_curve']))
        return data

    @cached_property
    def x_be(self):
        """Returns the binding energy x-values as a Numpy array"""
        if self.region['analysis_method'] != 'XPS':
            message = "Analysis_method is {}".format(
                self.region['analysis_method'])
            raise NotXPSException(message)

        # Calculate the x binding energy values
        data = self.region['excitation_energy'] - self.x
        _LOG.debug('Creating x_be values from {} to {} in {} steps'.format(
            data.min(), data.max(), data.size))
        return data

    @property
    def iter_cycles(self):
        """Returns a generator of cycles

        Each cycle is in itself a generator of lists of scans. To
        iterate over single scans do:

        .. code-block:: python

         for cycle in self.iter_cycles:
             for scans in cycle:
                 for scan in scans:
                     print scan

        or use :py:attr:`iter_scans`, which do just that.
        """
        for cycle in self.cycles:
            yield (scan['counts'] for scan in cycle['scans'])

    @property
    def iter_scans(self):
        """Returns an generator of single scans, which in themselves are Numpy
        arrays

        """
        for cycle in self.iter_cycles:
            for scans in cycle:
                for scan in scans:
                    yield scan

    @cached_property
    def y_avg_counts(self):
        """Returns the average counts as a Numpy array"""
        vstack = np.vstack(self.iter_scans)
        data = vstack.mean(axis=0)
        _LOG.debug('Creating {} y_avg_counts values from {} scans'.format(
            data.size, vstack.shape[0]
        ))
        return data

    @cached_property
    def y_avg_cps(self):
        """Returns the average counts per second as a Numpy array"""
        try:
            data = self.y_avg_counts / self.region['dwell_time']
            _LOG.debug('Creating {} y_avg_cps values'.format(data.size))
        except TypeError:
            data = None
        return data

    @property
    def unix_timestamp(self):
        """Returns the unix timestamp of the first cycle"""
        for cycle in self.cycles:
            return cycle.get('time')
        return None


class NotXPSException(Exception):
    """Exception for trying to interpret non-XPS data as XPS data"""
    pass
