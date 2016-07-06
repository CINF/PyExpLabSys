#!/bin/env python3

"""File parser for the Omicron "Flattener" format"""

import logging
_LOG = logging.getLogger('omicron')
_LOG.addHandler(logging.NullHandler())


class Flattener(object):
    """Class that represents a file in the Flattener format"""

    def __init__(self, filepath):
        """Initialize the Flatterner file

        Args:
            filepath (unicode): The path of the file to be parsed
        """
        self._file = open(filepath, 'rb')
        _LOG.info('Parse flattener file: %s', filepath)
        
        


def parse_test():
    """Test parsing different files"""
    logging.basicConfig(level=logging.DEBUG)
    Flattener('/home/cinf/PyExpLabSys/tests/testdata/omicron_flattener/'
              'default_2016May11-091439_ESpHybrid_NanoSAM-ESpHybrid_NanoSAM_XPS'
              '--1_1.Detector.7_flat')
    


if __name__ == "__main__":
    parse_test()
