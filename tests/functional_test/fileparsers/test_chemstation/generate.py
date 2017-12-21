
"""Generate chemstation test data from working configuration"""

import json
from os import path

from PyExpLabSys.file_parsers.chemstation import Sequence

THIS_DIR = path.dirname(path.realpath(__file__))
SEQUENCES = (
    Sequence(path.join(THIS_DIR, 'def_GC 2015-01-13 11-16-24')),
    Sequence(path.join(THIS_DIR, '05102016_CAL_CH4_5CM3')),
)


def generate_sequence_metadata():
    """Generate sequence metadata"""
    out = []
    for seq in SEQUENCES:
        meta = seq.metadata
        meta['sequence_start_timestruct_CONVERT'] = tuple(
            meta.pop('sequence_start_timestruct')
        )
        out.append(meta)

    with open('sequence_metadata.json', 'wb') as file_:
        json.dump(out, file_, indent=4)


def generate_full_sequence_data():
    """Generate full sequence data"""
    out = SEQUENCES[0].full_sequence_dataset()
    with open('chemstation_data.json', 'wb') as file_:
        json.dump(out, file_, indent=4)

def generate_injection_metadata():
    """Generate injections metadata"""
    out = []
    for seq in SEQUENCES:
        injection_metadata = dict(seq.injections[0].metadata)
        for key in list(injection_metadata.keys()):
            if key.endswith('_timestruct'):
                injection_metadata[key + '_CONVERT'] =\
                    tuple(injection_metadata.pop(key))
        out.append(injection_metadata)
    with open('injection_metadata.json', 'wb') as file_:
        json.dump(out, file_, indent=4)

generate_sequence_metadata()
generate_full_sequence_data()
generate_injection_metadata()
