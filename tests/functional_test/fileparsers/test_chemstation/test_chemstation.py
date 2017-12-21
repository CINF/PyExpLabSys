
"""Functional tests for the chemstation parser"""

from __future__ import unicode_literals, print_function
from os import path
import json
import time
import pytest

import numpy

from PyExpLabSys.file_parsers.chemstation import Sequence, CHFile
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

THIS_DIR = path.dirname(path.realpath(__file__))
DATA_FILE = path.join(THIS_DIR, 'chemstation_data.json')
INJECTION_METADATA_PATH = path.join(THIS_DIR, 'injection_metadata.json')
SEQUENCE_METADATA_PATH = path.join(THIS_DIR, 'sequence_metadata.json')
CHFILE = path.join(THIS_DIR, 'TCD3C.ch')
CHDATA = path.join(THIS_DIR, 'ch_metadata.json')


# Load sequences and expected metadata
SEQUENCES = (
    Sequence(path.join(THIS_DIR, 'def_GC 2015-01-13 11-16-24')),
    Sequence(path.join(THIS_DIR, '05102016_CAL_CH4_5CM3')),
)
with open(SEQUENCE_METADATA_PATH, 'rb') as file__:
    SEQUENCE_METADATA = json.load(file__)
with open(INJECTION_METADATA_PATH, 'rb') as file__:
    INJECTION_METADATA = json.load(file__)


# Helper functions
def fix_converted(data):
    """Convert unix time stamps to timestructs

    JSON cannot serialize timestructs, so we store lists with the
    components instead. The values that needs to be converted are
    marked with _CONVERT on the key

    """
    modified = dict(data)
    for key in data:
        if key.endswith('_CONVERT'):
            new_key = key.replace('_CONVERT', '')
            modified[new_key] = time.struct_time(modified.pop(key))
    return modified


def to_int(number):
    """Convert floats to ints, to make it easier to compare"""
    return int(number * 10000)


def convert_full_dataset(full_dataset):
    """Convert full dataset so it is comparables"""
    out = {}
    for key, value in full_dataset.items():
        if '(' in key:
            # If it is a key that contains a float, convert that key
            # to a (str, int) pair
            #
            # The key looks like: FID2 B, Back Signal - CH4 (10.8715314865113)
            new_key = (
                key.split('(')[0],
                to_int(float(key.split('(')[1].strip(')')))
            )
        else:
            new_key = key
        # Convert all the floats in the values to ints
        out[new_key] = [[to_int(item) for item in pair] for pair in value]
    return out


# Tests
@pytest.mark.parametrize("sequence,expected", zip(SEQUENCES, SEQUENCE_METADATA))
def test_metadata(sequence, expected):
    """Test the sequence metadata"""
    metadata = sequence.metadata
    expected = fix_converted(expected)
    assert metadata == expected


def test_data():
    """Test the sequence data"""
    dataset = SEQUENCES[0].full_sequence_dataset()
    dataset = convert_full_dataset(dataset)
    with open(DATA_FILE) as file_:
        saved_dataset = json.load(file_)
    saved_dataset = convert_full_dataset(saved_dataset)
    assert dataset == saved_dataset


@pytest.mark.parametrize("sequence,expected", zip(SEQUENCES, INJECTION_METADATA))
def test_injection_metadata(sequence, expected):
    """Test the metadata for the injections"""
    injection_metadata = fix_converted(dict(sequence.injections[0].metadata))
    expected = fix_converted(dict(expected))
    for dict_ in (injection_metadata, expected):
        for key in ('injection_date_unixtime', 'results_created_unixtime'):
            dict_[key] = to_int(dict_[key])
    assert injection_metadata == expected


def test_ch_file():
    """Test the parse ChFile class"""
    ch_file = CHFile(CHFILE)

    # Check the data (it is primitively "hashed" as the sum of the array)
    saved_times_sum = 8441.24998112
    saved_values_sum = -2242.09973958
    assert numpy.isclose(saved_times_sum, ch_file.times.sum())
    assert numpy.isclose(saved_values_sum, ch_file.values.sum())

    metadata = ch_file.metadata
    metadata['datetime'] = time.mktime(metadata['datetime'])
    # Test metadata
    with open(CHDATA, 'r') as file_:
        saved_metadata = json.load(file_)
    assert saved_metadata == ch_file.metadata
