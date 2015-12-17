from __future__ import print_function
import os
import time
from PyExpLabSys.file_parsers.chemstation import Sequence
from PyExpLabSys.common.database_saver import DataSetSaver
from PyExpLabSys.common.database_saver import CustomColumn


# Instantiate the data set saver
data_set_saver = DataSetSaver('measurements_dummy','xy_values_dummy','dummy','dummy')
data_set_saver.start()

# Get the set of aleady uploaded files
already_uploaded = data_set_saver.get_unique_values_from_measurements('relative_path')
print('Fetched relative paths for {} known sequences'.format(len(already_uploaded)))

# This is the measurement path, should be generated somehow
basefolder = '/home/kenni/Dokumenter/chemstation parser'
sequence_identifyer = 'sequence.acaml'

for root, dirs, files in os.walk(basefolder):
    if sequence_identifyer in files:
        #check if file is known
        relative_path = root.replace(basefolder, '').strip(os.sep)
        if relative_path in already_uploaded:
            continue

        print('Found new sequence for upload: {}'.format(relative_path), end='')
        sequence = Sequence(root)
        metadata = sequence.metadata.copy()
        metadata['relative_path'] = relative_path
        metadata['time'] = CustomColumn(time.mktime(metadata.pop('sequence_start')), 'FROM_UNIXTIME(%s)')
        metadata['type'] = 14
        data_set = sequence.full_sequence_dataset() 
        
        for label,data in data_set.items():
            data_set_metadata = metadata.copy()
            data_set_metadata['label'] = label  
            codename = relative_path+label
            x,y = zip(*data)
            data_set_saver.add_measurement(codename, data_set_metadata)
            data_set_saver.save_points_batch(codename, x, y)
        print(' ... UPLOADED')
        #upload file    

data_set_saver.stop()
       


