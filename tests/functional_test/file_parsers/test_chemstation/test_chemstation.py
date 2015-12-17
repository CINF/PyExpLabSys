
from __future__ import unicode_literals, print_function
import os
import json
import time
import pytest

from PyExpLabSys.file_parsers.chemstation import Sequence

THIS_FILE_DIR = os.path.dirname(os.path.realpath(__file__))
SEQUENCE_FILE = os.path.join(THIS_FILE_DIR, 'def_GC 2015-01-13 11-16-24')
DATA_FILE = os.path.join(THIS_FILE_DIR, 'chemstation_data.json')
INJECTION_METADATA = os.path.join(THIS_FILE_DIR, 'injection_metadata.json')



# Sequence metadata
SEQUENCE_METADATA = {
    u'method_name': 'Sine14.M',
    u'sequence_start': time.struct_time((2015, 1, 13, 11, 16, 24, 1, 13, -1)),
    u'sample_name': u'NI cat'
}


# Fixtures
@pytest.fixture(scope='module')
def sequence():
    return Sequence(SEQUENCE_FILE)


# Tests
def test_metadata(sequence):
    """Test the sequence metadata"""
    metadata = sequence.metadata
    assert SEQUENCE_METADATA == metadata


def test_data(sequence):
    """Test the sequence data"""
    dataset = sequence.full_sequence_dataset()
    with open(DATA_FILE) as file_:
        saved_dataset = json.load(file_)
    assert dataset == saved_dataset

def test_injection_metadata(sequence):
    """Test the metadata for the injections"""
    injection_metadata = [inj.metadata  for inj in sequence.injections]
    # Replace timestruct with unixtime, which can be serialized with json
    for metadata in injection_metadata:
        metadata['sequence_start'] = time.mktime(metadata['sequence_start'])

    # Load the correct values
    with open(INJECTION_METADATA) as file_:
        loaded_metadata = json.load(file_)

    assert injection_metadata == loaded_metadata

    
