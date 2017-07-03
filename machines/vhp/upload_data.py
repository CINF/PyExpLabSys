from __future__ import print_function
import os
import time
import logging
# logging.basicConfig(level=logging.DEBUG)  # Comment in for more logging output
from collections import defaultdict
from PyExpLabSys.file_parsers.chemstation import Sequence

### REMOVE after database move is complete

from PyExpLabSys.common import database_saver
database_saver.HOSTNAME = 'cinfsql'

### REMOVE after database move is complete

from PyExpLabSys.common.database_saver import DataSetSaver
from PyExpLabSys.common.database_saver import CustomColumn
import credentials


# Instantiate the data set saver
data_set_saver = DataSetSaver('measurements_vhp_setup', 'xy_values_vhp_setup',
                              credentials.USERNAME, credentials.PASSWORD)
data_set_saver.start()

# Get the set of aleady uploaded files
already_uploaded = data_set_saver.get_unique_values_from_measurements('relative_path')
print('Fetched relative paths for {} known sequences'.format(len(already_uploaded)))

# This is the measurement path, should be generated somehow
basefolder = '/home/cinf/o/FYSIK/list-SurfCat/setups/vhp-setup'
sequence_identifyer = 'sequence.acaml'

# Find the active month
newest = None
highest_value = 0
for dir_ in os.listdir(basefolder):
    dir_split = dir_.split(' ')
    if len(dir_split) != 2:
        continue
    try:
        month, year = [int(component) for component in dir_split]
    except ValueError:
        continue
    value = year * 100 + month
    if value > highest_value:
        newest = dir_
        highest_value = value

if newest is None:
    raise RuntimeError('Unable to find month folder')

print('Found newest folder: "{}" in basefolder'.format(newest))

for root, dirs, files in os.walk(os.path.join(basefolder, newest)):
    if sequence_identifyer in files:
        # Check if file is known
        relative_path = root.replace(basefolder, '').strip(os.sep)
        print(relative_path)
        if relative_path in already_uploaded:
            continue

        # Load the sequence
        print('Found new sequence for upload: {} '.format(relative_path))
        try:
            sequence = Sequence(root)
        except ValueError as exception:
            if exception.args[0].startswith('No injections in sequence'):
                print(' ... No injections in this sequence')
                continue
            else:
                raise exception

        # Upload the sequence summary data
        metadata = sequence.metadata.copy()
        metadata['relative_path'] = relative_path
        metadata['time'] = CustomColumn(time.mktime(metadata.pop('sequence_start')), 'FROM_UNIXTIME(%s)')
        metadata['type'] = 20
        # We don't use these columns, but they are setup in the database without default
        # values, so to avoid warnings we fill them in
        metadata['sem_voltage'] = 0.0
        metadata['preamp_range'] = 0.0
        data_set = sequence.full_sequence_dataset() 
        
        for label, data in data_set.items():
            data_set_metadata = metadata.copy()
            data_set_metadata['label'] = label  
            codename = relative_path+label
            x, y = zip(*data)
            data_set_saver.add_measurement(codename, data_set_metadata)
            data_set_saver.save_points_batch(codename, x, y)
        print('   Summary datasets uploaded........: {}'.format(len(data_set)))

        # Do not uploade raw data right now, since we have database troubles
        continue

        # Upload the raw spectra
        raw_spectra = defaultdict(list)
        for injection in sequence.injections:
            for detector_name, rawfile in injection.raw_files.items():
                raw_spectra[detector_name].append((injection.metadata['injection_number'], rawfile))

        for detector, spectra in raw_spectra.items():
            for injection, spectrum in spectra:
                metadata_translation = (
                    ('sample', 'sample_name'),
                    ('method', 'method_name'),
                    ('units', 'unit'),
                    ('detector', 'detector'),
                )
                metadata_raw = {new: spectrum.metadata[orig] for orig, new in metadata_translation}
                metadata_raw.update({
                    'relative_path': relative_path,
                    'injection': injection,
                    'label': detector.split('.')[0] + ' Inj. ' + str(injection),
                    'type': 21,
                    'time': CustomColumn(time.mktime(spectrum.metadata['datetime']), 'FROM_UNIXTIME(%s)'),
                })

                # We don't use these columns, but they are setup in the database without default
                # values, so to avoid warnings we fill them in
                metadata_raw['sem_voltage'] = 0.0
                metadata_raw['preamp_range'] = 0.0

                codename = metadata_raw['relative_path'] + metadata_raw['label']
                data_set_saver.add_measurement(codename, metadata_raw)
                data_set_saver.save_points_batch(codename, spectrum.times, spectrum.values)

            print('   Uploaded raw spectra for {: <8}: {}'.format(detector, len(spectra)))
            data_set_saver.wait_for_queue_to_empty()

        print('   DONE')


# Enable logging at this point to show the user that they are waiting for the saver to save information
logging.basicConfig(level=logging.INFO)
data_set_saver.stop()
print('ALL DONE')

