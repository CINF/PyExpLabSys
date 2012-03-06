from nidaqmx import AnalogInputTask
import numpy as np
task = AnalogInputTask()
task.create_voltage_channel('Dev2/ai2', terminal = 'rse', min_val=-1.0, max_val=1.0)
task.configure_timing_sample_clock(rate = 1000.0)
task.start()
data = task.read(2000, fill_mode='group_by_channel')
del task
from pylab import plot, show
x = np.arange(0,2,0.001)
plot (x,data[0],'ro')

print np.sum(data)/2000



show ()