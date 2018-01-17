#!/usr/bin/env python
# -*- coding: utf-8 -*-
#pylint: disable=R0903,E1101
# Globally disable warnings about to few public methods

""" This file is used to parse xps data from xml files from the SPECS
program and send it to the cinf database. In this file format the
spectra (called regions) are containd in so-called region groupd inide
the files. This structure is mirrored in the data structure below,
therefore there is a Parse class used to do all the heavy lifting with
the finding the relevant files and sending them to the db and the
three classes File, RegionGroup and Region which are used to represent
those parts of the datafiles.
"""

########## EDIT POINT ### Global settings for the script are added here
BASEPATH = '/home/stm312-xps/Desktop/Shared/OurData/XPS'
#BASEPATH = 'C:\Documents and Settings\stm312\My Documents\OurData\XPS'
#'C:\Documents and Settings\stm312\My Documents\python scripts\XPS'
# C:\Documents and Settings\stm312\My Documents\OurData\XPS
DATA_FILE_EXTENSION = '.xml'
EASUREMENTS_TABLE = 'measurements_stm312'
XYVALUES_TABLE = 'xy_values_stm312'
########## EDIT POINT ### Global settings for the script are added here

import os
from xml.etree import ElementTree
import re
import time

import numpy as np
import MySQLdb

import credentials


def status_msg(string, status):
    """ Print out status message """
    if status:
        print string.ljust(74) + '[OK]'
    else:
        print string.ljust(70) + '[FAILED]'


def form_unique_name(string):
    """ This method creates as much of the path as is necessary to create a
    unique name that will identidfy this file in the db.
    """
    return string[len(BASEPATH) + 1:].replace('/', '\\')


def find_child_element(xml, tag, name, attrib_value=None):
    """ Function to get the first child element with tag 'tag' and that has a
    attribute named 'name'. Usefull when the tag names are not descriptive.
    """
    if attrib_value is None:
        for element in xml.getchildren():
            if element.tag == tag and name in element.attrib:
                return element
    else:
        for element in xml.getchildren():
            if element.tag == tag and name in element.attrib and\
                    element.attrib[name] == attrib_value:
                return element


def extract_date(string):
    """ Extract a date from the filename. The stm312 setup has used 3
    different ways of writing dates in the filenames, so all 3 are
    tested below. For other setups who are more consistent this could
    be reduced to just one pattern
    """
    filename = os.path.basename(string)
    noext = os.path.splitext(filename)[0]

    expressions = [
        # XPS_201307121140a      YYYYmmDDHHMM
        [r'XPS_([0-9]{12}).*', '%Y%m%d%H%M'],
        # XPS_031105a.xml      DDmmyy
        #[r'XPS_([0-9]{6}).*', '%d%m%y'],
        # XPS_07aug22b_countratetest      YYmmmDD
        #,[r'XPS_([0-9]{6})[a-zA-Z].*', '%d%m%y'],
        # XPS_07aug22b_countratetest      YYmmmDD
        #,[r'XPS_([0-9]{2}[a-zA-Z]{3}[0-9]{2}).*', '%y%b%d'],
        # XPS_20080111a                   YYYYMMDD
        #,[r'XPS_([0-9]{8}).*', '%Y%m%d']
    ]
    date_out = None
    for exp in expressions:
        try:
            res = re.search(exp[0], noext)
            pure = res.group(1)
            try:
                date_out = time.mktime(time.strptime(pure, exp[1]))
            except ValueError:
                print '   Date could not be parsed:', pure
        except (AttributeError, IndexError):
            pass
    if date_out is None:
        print '   Filename pattern unknown:', noext
    return date_out


class Parse(object):
    """ Main class for finding, parsing and sending xps data files to the db
    """

    def __init__(self, basepath, extension, tables):
        """ Initialize class variables """
        self.tables = tables
        self.basepath = basepath
        self.data_file_extension = extension

        self.new_data_files = []
        status_msg('Created parser', True)
        database = MySQLdb.connect(host='servcinf-sql', user=credentials.USER,
                                   passwd=credentials.PASSWD, db='cinfdata')
        self.cursor = database.cursor()
        status_msg('Created database connection', True)

    def find_new_files(self):
        """ Find data files not already in the db
        Uses: self._find_data_files
              self._check_for_duplicates
        """
        in_file_system = self._find_data_files(self.basepath,
                                               self.data_file_extension, [])
        status_msg('Search for data files. Found: {0}'.format(
            len(in_file_system)), True
        )
        status_msg('Check that there are no duplicate filenames', True)
        in_db = self._get_files_in_db()
        status_msg('Get list of files in data base. Found: {0}'.format(
            len(in_db)), True
        )
        for filename in in_file_system:
            # Filename has been added to the database both where a part of the
            # path was a part of the unique name and where it was not,
            # therefore we need to check for both AND we ignore filenames that
            # start with IGNORE
            if form_unique_name(filename) not in in_db and\
               os.path.basename(filename) not in in_db and not\
               os.path.basename(filename).startswith('IGNORE'):
                self.new_data_files.append(filename)

        print  # Adds a new line to the statusses before parsing
        status_msg('Collecting new files. Found: {0}'.format(
            len(self.new_data_files)), True
        )

    def _find_data_files(self, current_basepath, extension, paths):
        """ Standard recursive algorithm to traverse current_basepath
        and look for file with extension.

        NOTE! No care has be taken to handle links, so if these accour
        inside the data directories, then succes is not guarantied.
        """
        try:
            files = os.listdir(current_basepath)
            files.sort()
            for filename in files:
                if os.path.isdir(os.path.join(current_basepath, filename)):
                    paths = self._find_data_files(
                        os.path.join(current_basepath, filename), extension,
                        paths
                    )
                else:
                    if os.path.splitext(filename)[1] == extension:
                        paths.append(os.path.join(current_basepath, filename))
        except OSError:
            print 'Access Denied: ' + current_basepath

        return paths

    def _get_files_in_db(self):
        """ Fetch the list of files from the database """
        query = 'SELECT DISTINCT file_name FROM {0};'.format(
            self.tables['measurements'])
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        files = [ele[0] for ele in result if ele[0] is not None]
        return files

    def add_to_db(self):
        """ Form the file objects and add them to the database """
        for filename in self.new_data_files:
            unique_name = form_unique_name(filename)
            extracted_date = extract_date(filename)
            if extracted_date is not None:
                # If we can parse the date from the filename we parse the file
                file_ = File(filename, unique_name, extracted_date)
                content = file_.get_content()
                for element in content:
                    # If each of the spectra in the file has data, we
                    # add it to the data base
                    if element[1] is not None:
                        self.add_to_db_single(element)
                        status_msg('Elements of file {0} added to db'.format(
                            unique_name), True)
            else:
                status_msg('File {0} not added, unknown filename format'.
                           format(unique_name), False)

    def add_to_db_single(self, element):
        """ Add a single object to the database """
        def quot(string):
            """ Replace " with ' in text strings that goes into the
            db, right now it is only done on the name, but it should
            be done on all fields that might contain such characters
            """
            return string.replace('"', "'")

        # Make entry i measurements table
        query = ('INSERT INTO {table} SET '
                 'time=FROM_UNIXTIME({time}), '
                 'type=2, '
                 'timestep={timestep}, '
                 'comment="{comment}", '
                 'pass_energy={pass_energy}, '
                 'excitation_energy={excitation_energy}, '
                 'number_of_scans={number_of_scans}, '
                 'project="{project}", '
                 'file_name="{file_name}", '
                 'name="{name}";').format(
            table=self.tables['measurements'],
            time=element[0]['date'],
            timestep=element[0]['dwell_time'],
            comment=element[0]['unique_name'],
            pass_energy=element[0]['pass_energy'],
            excitation_energy=element[0]['excitation_energy'],
            number_of_scans=element[0]['num_scans'],
            project=element[0]['project'],
            file_name=element[0]['unique_name'].replace('\\', '\\\\'),
            name=quot(element[0]['name']))

        # Christian, comment this in to see a list of metadata
        #print element[0]
        self.cursor.execute(query)  # COMMENT

        # Get the id of it
        query = ('select id from {table} where type=2 '
                 'order by id desc limit 1;').\
            format(table=self.tables['measurements'])
        self.cursor.execute(query)
        id_ = self.cursor.fetchall()[0][0]

        # Add the data to xy_values table in chunks of 100 data points
        counter = 0
        query_reset = 'INSERT INTO {table} (measurement, x, y) VALUES'.format(
            table=self.tables['xy'])
        query = query_reset
        # element[1] is tuple of data: (Array(x0, x1, x2), Array(y0, y1, y2)).
        # The zip statement (where * pulls out both value) turns it into:
        # [(x0, y0), (x1, y1), (x2, y2)]
        for x_value, y_value in zip(*element[1]):
            counter += 1
            query += '({0},{1},{2})'.format(id_, x_value, y_value)
            if counter < 100:
                query += ','
            else:
                query += ';'
                self.cursor.execute(query)
                counter = 0
                query = query_reset
        # Remember to write the last less than 100 points
        if query != query_reset:
            # Remove the last , and add a ;
            query = query[0: -1] + ';'
            self.cursor.execute(query)


class File(object):
    """ This is the top structure for a parsed file. It contais a list of
    RegionGroups
    """
    def __init__(self, filepath, unique_name, extracted_date):
        self.unique_name = unique_name
        self.extracted_date = extracted_date
        xml = ElementTree.parse(filepath)
        self.region_groups = []
        for regiongroupseq in xml.getroot():
            for regiongroup in regiongroupseq:
                self.region_groups.append(RegionGroup(regiongroup))

    def get_content(self):
        """ Return all regions in this file """
        content = []
        for regiongroup in self.region_groups:
            for region in regiongroup.get_content():
                # Add date, unique_name and project to the metadata
                region[0]['date'] = self.extracted_date
                region[0]['unique_name'] = self.unique_name
                try:
                    project = os.path.split(
                        os.path.split(self.unique_name)[0]
                    )[1]
                except IndexError:
                    project = ''
                region[0]['project'] = project
                content.append(region)
        return content


class RegionGroup(object):
    """ Class that represents a region group """
    def __init__(self, xml):
        for child in xml.getchildren():
            if child.tag == 'string' and 'name' in child.attrib:
                self.reg_group_name = child.attrib['name']
            if child.tag == 'sequence' and 'name' in child.attrib and\
                    child.attrib['name'] == 'regions':
                regions_xml = child

        self.regions = []
        for child in regions_xml.getchildren():
            if child.tag == 'struct' and 'type_name' in child.attrib and\
                    child.attrib['type_name'] == 'RegionData':
                self.regions.append(Region(child))

    def get_content(self):
        """ Return all the regions in this regions groups """
        content = []
        for reg in self.regions:
            reg_content = reg.get_content()
            reg_content[0]['reg_group_name'] = self.reg_group_name
            content.append(reg_content)
        return content


class Region(object):
    """ Class that represents a region """

    def __init__(self, xml):  # pylint: disable=R0912,R0914
        regiondef = find_child_element(xml, 'struct',
                                       'type_name', 'RegionDef')

        self.parameters = {}
        for element in xml.getchildren():
            if element.attrib['name'] == 'name':
                self.parameters['name'] = element.text
            elif element.attrib['name'] == 'region':
                regiondef = element
            elif element.attrib['name'] == 'cycles':
                cycles = element

        # Get parameters
        for element in regiondef:
            self.parameters[element.attrib['name']] = element.text

        # Parse out way though the xml to the data
        cycle = find_child_element(cycles, 'struct', 'type_name',
                                   'Cycle')
        scans = find_child_element(cycle, 'sequence', 'name', 'scans')

        # Find be start and end
        x_data = None
        try:
            be_start = \
                np.float(self.parameters['excitation_energy']) -\
                np.float(self.parameters['kinetic_energy'])
            be_end = np.float(be_start) - \
                (np.float(self.parameters['values_per_curve']) - 1) * \
                np.float(self.parameters['scan_delta'])
            if not (be_start < -10 or be_end < -10):
                x_data = np.linspace(
                    be_start, be_end,
                    np.float(self.parameters['values_per_curve'])
                )
        except TypeError:
            x_data = None

        # data becomes a list of scans, of which each is a list of counts
        data = []
        for scan in scans.getchildren():
            scandata = find_child_element(scan, 'sequence', 'name', 'counts')
            counts = find_child_element(scandata, 'ulong', 'type_name',
                                        'Counts')
            try:
                dat = [np.float(count) for count in
                       counts.text.strip('\n').split('\n')]
            except AttributeError:
                dat = None
            data.append(dat)

        if None not in data:
            y_data = np.mean(np.array(data, dtype=float), axis=0)
        else:
            y_data = None

        self.spectrum = None
        if (x_data is not None and y_data is not None and
                len(x_data) == len(y_data)):
            self.spectrum = (x_data, y_data)

    def get_content(self):
        """ Return the parameters and the spectrum """
        return self.parameters, self.spectrum

if __name__ == '__main__':
    PARSE = Parse(basepath=BASEPATH,
                  extension=DATA_FILE_EXTENSION,
                  tables={'measurements': MEASUREMENTS_TABLE,
                          'xy': XYVALUES_TABLE}
                  )

    PARSE.find_new_files()
    PARSE.add_to_db()
    raw_input("\nUploading of XPS file complete, press ENTER to exit...")
