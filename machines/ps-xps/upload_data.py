"""Uploads the XPS and ISS measurements from the parallel screening setup"""

from __future__ import print_function
import os
from collections import namedtuple
import json
import MySQLdb
import credentials  # pylint: disable=import-error
from PyExpLabSys.file_parsers.specs import SpecsFile

DATAPATH = 'C:\\Users\\cinf\\Documents\\shared with vm\\XPS and ISS\\'\
           'Dati XPS - ISS'
# Database setup
CONNECTION = MySQLdb.connect('servcinf-sql', credentials.USERNAME,
                             credentials.PASSWORD, 'cinfdata')
CURSOR = CONNECTION.cursor()
# Named tuple for data file paths
DataFile = namedtuple('data_file', ('fullpath', 'db_path'))
# List of metadata fields names, [in_file, as_in_db]
METADATAFIELDS = [
    ['dwell_time', 'dwell_time'],
    ['scan_delta', 'energy_step'],
    ['excitation_energy', 'excitation_energy'],
    ['num_scans', 'number_of_scans'],
    ['pass_energy', 'pass_energy'],
    ['effective_workfunction', 'workfunction'],
    ['analyzer_lens', 'analyzer_lens'],
]
# Table names
MEASUREMENTS_TABLE = 'measurements_ps'
XY_TABLE = 'xy_values_ps'


def json_default(_):
    """Returns the default string when an item cannot be JSON serailizable"""
    return 'NON JSON SERIALIZABLE'


def get_list_of_datafiles():
    """Returns a list of datafiles as DataFile named tuples"""
    data_files = []

    # Walk the path that contains the data files
    for root, _, filenames in os.walk(DATAPATH):
        for filename in filenames:
            # Check the extension
            _, ext = os.path.splitext(filename)
            if ext.lower() != '.xml':
                continue

            # Create the full filepath and strip DATAPATH for the db
            filepath = os.path.join(root, filename)
            if not filepath.startswith(DATAPATH):
                message = 'Cannot strip DATAPATH from full filepath'
                raise Exception(message)
            db_filepath = filepath.split(DATAPATH)[1].lstrip(os.sep)
            data_files.append(DataFile(filepath, db_filepath))

    return data_files


def get_files_in_db():
    """Returns a set of files in the database"""
    query = 'select DISTINCT(file_name) from {} where type=2 or type=3'.format(
        MEASUREMENTS_TABLE)
    CURSOR.execute(query)
    files = set()
    for row in CURSOR.fetchall():
        if row[0] is not None and row[0] not in files:
            files.add(row[0])
    return files


def send_file_to_db(specsfile, db_path):
    """Sends a data file to the database"""
    print('#### Sending in file:', db_path)
    for region_group in specsfile:
        print('## Sending in group:', region_group.name)
        for region in region_group:
            send_region_to_db(specsfile, region_group, region, db_path)


def send_region_to_db(specsfile, region_group, region, db_path):
    """Sends a region to the db"""
    # Check for good data
    print('Sending in region:', region.name)
    if region.region['analysis_method'] == 'XPS':
        xdata = region.x_be
    else:
        xdata = region.x
    ydata = region.y_avg_cps

    if xdata is None:
        print('x data is None, skipping this region')
        return
    if ydata is None:
        print('y data is None, skipping this region')
        return
    if xdata is not None and ydata is not None and len(xdata) != len(ydata):
        print('x and y data has different lengths, skipping this region')
        return

    db_id = send_region_metadata(specsfile, region_group, region, db_path)
    send_region_data(xdata, ydata, db_id)


def send_region_metadata(specsfile, region_group, region, db_path):
    """Send the metadata for a region"""
    # Get metadata from region
    metadata = {new_key: region.region[key] for key, new_key in METADATAFIELDS}
    # Get the rest of the metadata
    metadata['name'] = region.name
    metadata['extra_json'] = json.dumps(region.info, default=json_default)
    metadata['group_name'] = region_group.name
    metadata['time'] = specsfile.unix_timestamp
    metadata['file_name'] = db_path

    # Set type and reset excitation energy for ISS
    if region.region['analysis_method'] == 'ISS':
        metadata.update({'type': 3, 'excitation_energy': None})
    elif region.region['analysis_method'] == 'XPS':
        metadata.update({'type': 2})
    else:
        message = 'Unknown analysis method: "{}"'.format(
            region.region['analysis_method'])
        raise ValueError(message)

    # Generate the SQL and insert the entry
    keystring = 'time'
    valuestring = 'FROM_UNIXTIME(%s)'
    values = [metadata.pop('time')]
    for key, value in metadata.items():
        keystring += ', {}'.format(key)
        valuestring += ', %s'
        values.append(value)

    query = 'INSERT INTO {} ({}) VALUES ({});'.format(
        MEASUREMENTS_TABLE, keystring, valuestring)
    print('Sending in {} items of metadata'.format(len(values)))
    #print("Q", query)
    #print("K", keystring)
    metadata.pop('extra_json')
    #print(values[0])
    #print(metadata)
    CURSOR.execute(query, values)
    CONNECTION.commit()

    # Get the id
    query = 'select id from {} where time=FROM_UNIXTIME(%s) and type=%s '\
            'order by id desc limit 1'.format(MEASUREMENTS_TABLE)
    values = [values[0], metadata['type']]
    CURSOR.execute(query, values)
    return CURSOR.fetchall()[0][0]


def send_region_data(xdata, ydata, db_id):
    """Send the region data to the db"""
    query = 'INSERT INTO {} (measurement, x, y) VALUES (%s, %s, %s)'.format(
        XY_TABLE)
    ids = [db_id] * len(xdata)
    print('Sending in {} points'.format(len(xdata)))
    CURSOR.executemany(query, zip(ids, xdata, ydata))
    CONNECTION.commit()


def main():
    """Gets the list of files on harddrive and in db and uploads new ones"""
    data_files = get_list_of_datafiles()
    print('Found {} files on harddrive'.format(len(data_files)))
    db_files = get_files_in_db()
    print('Found {} files in db'.format(len(db_files)))
    new_files = []
    for data_file in data_files:
        if data_file.db_path not in db_files:
            new_files.append(data_file)
    print('Found {} new files'.format(len(new_files)))

    for index, data_file in enumerate(new_files):
        specsfile = SpecsFile(data_file.fullpath, encoding='iso-8859-1')
        send_file_to_db(specsfile, data_file.db_path)

    print('\nPress enter to exit')
    raw_input()


if __name__ == '__main__':
    main()
