# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import time
from PyExpLabSys.common.database_saver import  DataSetSaver, CustomColumn
import credentials

data_set_saver = DataSetSaver(
        'measurements_large_CO2_MEA',
        'xy_values_large_CO2_MEA',
        credentials.USERNAME,
        credentials.PASSWORD,
)
data_set_saver.start()

now = time.time()
now_custom_column = CustomColumn(now, 'FROM_UNIXTIME(%s)')

#CREATE TABLE `measurements_large_CO2_MEA` (
#  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
#  `time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
#  `type` int(10) unsigned NOT NULL COMMENT 'Type of measurement, as found in the types table',
#  `comment` varchar(128) NOT NULL COMMENT 'Comment',
#  `cathode_gas_type` varchar(128) NOT NULL COMMENT 'Cathode gas type',
#  `anode_gas_type` varchar(128) NOT NULL COMMENT 'Anode gas type',
#  `cathode_catalyst_description` varchar(128) NOT NULL COMMENT 'Cathode catalyst description',
#  `anode_catalyst_description` varchar(128) NOT NULL COMMENT 'Anode catalyst description',
#  `label` varchar(45) NOT NULL,
#  PRIMARY KEY (`id`)
#) ENGINE=MyISAM DEFAULT CHARSET=latin1 COMMENT='A single record pr. measurent run'

metadata = {
    'type': 14,
    'comment': "My Comment",
    'cathode_gas_type': "CO2",
    'anode_gas_type': "N2",
    'cathode_catalyst_description': "Magic",  #  "This is what it is made of: 4cm2"
    'anode_catalyst_description': "More Magic",
}
# Add the one custom column
metadata['time'] = now_custom_column

# Add all measurements
metadata['label'] = 'voltage'
data_set_saver.add_measurement('voltage', metadata)
metadata['label'] = 'current'
data_set_saver.add_measurement('current', metadata)

for n in range(100):
    x = float(n)
    y = time.time()
    y2 = y * 2
    data_set_saver.save_point('voltage', (x, y))
    print('voltage', x, y)
    data_set_saver.save_point('current', (x, y2))
    print('current', x, y)
    time.sleep(0.1)

data_set_saver.wait_for_queue_to_empty()
data_set_saver.stop()

time.sleep(3)