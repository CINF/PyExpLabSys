

import time
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn
import credentials

## EDIT HERE
comment = "First run"
## EDIT HERE




# Create data set saver object
data_set_saver = DataSetSaver(
    "measurements_dummy", "xy_values_dummy", credentials.USERNAME, credentials.PASSWORD,
)
data_set_saver.start()

# Create measurement specs i.e. entires entries in the metadata table
data_set_time = time.time()
metadata = {
    "time": CustomColumn(data_set_time, "FROM_UNIXTIME(%s)"), "comment": comment,
    "type" : 64, "preamp_range": 0, "sem_voltage": 0}

# Only the labels differ, so we generate the metadata with a loop
for label in ["p_korr", "i_korr", "total_korr", "ph_setpoint", "ph_value", "pump_rate"]:
    metadata["mass_label"] = label
    data_set_saver.add_measurement(label, metadata)




# http://pyexplabsys.readthedocs.io/common/database_saver.html#PyExpLabSys.common.database_saver.DataSetSaver.save_point
#data_set_saver.save_point()


for n in range(100):
    data_set_saver.save_point("p_korr", (n, n*2))


data_set_saver.stop()
