# pylint: disable=no-member

"""This module contains tests for specs parser"""

from __future__ import print_function
import re
import os
import codecs
import numpy as np
from PyExpLabSys.file_parsers.specs import SpecsFile
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


FIRST_CAP_RE = re.compile('(.)([A-Z][a-z]+)')
ALL_CAP_RE = re.compile('([a-z0-9])([A-Z])')
THIS_FILE_DIR = os.path.dirname(os.path.realpath(__file__))


def capital_to_underscore(string):
    """ Convert capital to lowercase and underscore
    Recipy partially from http://stackoverflow.com/a/1176023
    """
    string = string.replace('ber of ', '')
    string = string.replace('/', 'Per')
    string = string.replace(' ', '')
    string = FIRST_CAP_RE.sub(r'\1_\2', string)
    return ALL_CAP_RE.sub(r'\1_\2', string).lower()


def get_specs_region(filepath, region):
    """Get the specs region"""
    specs_file = SpecsFile(os.path.join(THIS_FILE_DIR, filepath))
    return specs_file.search_regions(region)[0]


def get_xy_data(filepath):
    """Get the xy region"""
    data = np.genfromtxt(os.path.join(THIS_FILE_DIR, filepath), delimiter='  ')
    return data


def get_xy_metadata(filepath):
    """Get the xy metadata"""
    metanames = (
        ('Region', str),
        ('Analysis Method', str),
        ('Analyzer', str),
        ('Analyzer Lens', str),
        ('Analyzer Slit', str),
        ('Number of Scans', int),
        ('Curves/Scan', int),
        ('Values/Curve', int),
        ('Dwell Time', float),
        ('Excitation Energy', float),
        ('Kinetic Energy', float),
    )
    meta = {}
    with open(os.path.join(THIS_FILE_DIR, filepath)) as file_:
        for line in file_:
            for metas in metanames:
                try:
                    first, second = line.split(':', 1)
                except ValueError:
                    continue
                if first == "# " + metas[0]:
                    second = second.strip()
                    converted_name = capital_to_underscore(metas[0])
                    # Assign and convert type
                    meta[converted_name] = metas[1](second)
            if len(meta) >= len(metanames):
                break
        else:
            raise SystemExit('Unable to find all metadata names')

    return meta


def test_xps_data():
    """Test XPS kinetic energy and average counts per second"""
    specs = get_specs_region('specs_xps_sample.xml', 'CrO overview Mg anode')
    xy_region = get_xy_data('specs_xps_sample.xy')
    assert np.allclose(xy_region[:, 0], specs.x)
    assert np.allclose(xy_region[:, 1], specs.y_avg_cps)


def test_xps_metadata():
    """Test the metadata extraction"""
    xy_meta = get_xy_metadata('specs_xps_sample.xy')
    region = get_specs_region('specs_xps_sample.xml', 'CrO overview Mg anode')
    # Special asserts
    assert xy_meta.pop('region') == region.name
    assert xy_meta.pop('analyzer') == region.analyzer_info['name']

    for key, value in xy_meta.items():
        if isinstance(value, float):
            assert np.isclose(value, region.region[key])
        else:
            assert value == region.region[key]
        print(region.region[key])


def test_iss_data():
    """Test ISS kinetic energy and average xps"""
    specs = get_specs_region('specs_iss_sample.xml', '1:3 Cu:Ru')
    xy_region = get_xy_data('specs_iss_sample.xy')
    assert np.allclose(xy_region[:, 0], specs.x)
    assert np.allclose(xy_region[:, 1], specs.y_avg_cps)


def test_iss_metadata():
    """Test the ISS metadata extraction"""
    xy_meta = get_xy_metadata('specs_iss_sample.xy')
    region = get_specs_region('specs_iss_sample.xml', '1:3 Cu:Ru')
    # Special asserts
    assert xy_meta.pop('region') == region.name
    assert xy_meta.pop('analyzer') == region.analyzer_info['name']

    for key, value in xy_meta.items():
        if isinstance(value, float):
            assert np.isclose(value, region.region[key])
        else:
            assert value == region.region[key]
        print(region.region[key])


if __name__ == '__main__':
    print("Execute with: py.test -v")
