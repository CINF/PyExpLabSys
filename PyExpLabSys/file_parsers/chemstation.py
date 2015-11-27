"""File parser for Chemstation files"""

from __future__ import print_function , unicode_literals
from collections import defaultdict

import codecs
import re
import os
import time
import math
from xml.etree import ElementTree


# Regular expressions quick guide
# () denotes a group that we want to capture
# [] denotes a group of characters to match
# * repeats the previous group if character
TABLE_RE = r'^ *([0-9]*) *([0-9\.]*)([A-Z ]*)([0-9\.]*) *([0-9e\.]*) *([0-9e\.]*) *([a-zA-Z0-9\?]*)$'

class Sequence(object):
    """The Sequence class for the Chemstation data format"""
    def __init__(self, sequence_dir_path):
        self.injections = []
        self.sequence_dir_path = sequence_dir_path
        self.metadata = {}
        self._parse()
        self._parse_metadata()
        
    def _parse_metadata(self):
        """
        """
        self.metadata['start_time'] = self.injections[0].sequence_start
        xml_file = ElementTree.parse(os.path.join(self.sequence_dir_path, 'sequence.acaml'))
        root = xml_file.getroot()
        print(root.findall('.//{urn:schemas-agilent-com:acaml15}Method'))
        # FIXME HERE HERE HER
        

    def _parse(self):
        """Parse the sequence"""
        sequence_dircontent = os.listdir(self.sequence_dir_path)
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
        return "<sequence object at {}>".format(self.sequence_dir_path)
        
    def full_sequence_dataset(self):
        """Generate molecule ('PeakName') specific dataset"""
        data = defaultdict(list)
        start_time = self.injections[0].unixtime
        for injection in self.injections:
            elapsed_time = injection.unixtime - start_time
            for measurement in injection.measurements:
                label = self.generate_data_label(measurement)
                data[label].append([elapsed_time, measurement['Area']])
        return data
                    
    def generate_data_label(self, measurement):
        """Return a label for a measurement
        
        For known molecule measurement gets detector-PeakName as label. For unnamed peaks
        label will be Unnamed and 0.01bin RetTime 
        """
        if measurement['PeakName'] == '?':
            lower = math.floor(measurement['RetTime'] * 100.0) / 100.0
            upper = math.ceil(measurement['RetTime'] * 100.0) / 100.0
            return 'Unnamed {:.2f}-{:.2f}'.format(lower, upper)
        else:
            # **measurement  turns into PeakName=..., detector=..., Type=...
            return '{detector}-{PeakName}'.format(**measurement)
            
class Injection(object):
    """The Injection class for the Chemstation data format"""

    def __init__(self, injection_dirpath):
        self.report_filepath = os.path.join(injection_dirpath, "Report.TXT")
        self.measurements = []  
        self.unixtime = None
        self.sequence_start = None
        self._parse_header()
        self._parse_file()
        
    def _parse_header(self):
        """Parse a header of Report.TXT file 
            
        Splitting file in two to get injection time in header 
        """
        with codecs.open(self.report_filepath, encoding='UTF16') as file_:
            for line in file_:
                if 'Area Percent Report' in line:
                    break
                elif line.startswith('Injection Date'): 
                    date_part = line.split(' : ')[1]
                    date_part = date_part.replace('Inj', '')
                    date_part = date_part.strip()
                    timestamp = time.strptime(date_part, '%d-%b-%y %I:%M:%S %p')
                    self.unixtime = time.mktime(timestamp)
                elif line.startswith('Last changed'):
                    date_part = line.split(' : ')[1]
                    date_part = date_part.split('by')[0].strip()
                    self.sequence_start = time.strptime(date_part, '%d-%b-%y %I:%M:%S %p')

    def _parse_file(self):
        """Parse a single Report.TXT file

        This file represents the results of a single injection

        MORE TO FOLLOW FIXME

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
            print('PROBLEMS WITH THE REGULAR EXPRESSION')
        groups = match.groups()
        if len(groups) < 7 :
            raise SystemExit()
        headers = ['Peak', 'RetTime', 'Type', 'Width', 'Area', 'Area%' , 'PeakName']  # Etc
        content_dict = dict(zip(headers, groups))
        for header in content_dict.keys():
            if header in ['RetTime', 'Width', 'Area', 'Area%']:
                content_dict[header] = float(content_dict[header])
            elif header == 'Peak':
                content_dict[header] = int(content_dict[header])
            else:
                content_dict[header] = content_dict[header].strip()
                        
        return content_dict
            
