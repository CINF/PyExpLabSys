from nidaqmx import AnalogInputTask
import numpy as np
import math


def readPressureAndTemperature(plot=False):
	RATE = 250.0
	DURATION = 5.0
	NUMBER_OF_SAMPLES = (int)(math.ceil(DURATION*RATE))

	task = AnalogInputTask()
	
	#Ion pump
	task.create_voltage_channel('Dev2/ai2', terminal = 'rse', min_val=-1.0, max_val=1.0)
	#Turbo temperature
	task.create_voltage_channel('Dev2/ai4', terminal = 'rse', min_val=0, max_val=1.0)

	task.configure_timing_sample_clock(rate = RATE)
	#print task.get_convert_clock_rate()
	task.set_convert_clock_rate(1000)
	#print task.get_convert_clock_rate()
	task.start()

	#print task.get_ai_convert_max_rate()

	data = task.read(NUMBER_OF_SAMPLES, fill_mode='group_by_channel')
	del task

	if plot:
		from pylab import plot, show
		x = np.arange(0,DURATION,1.0/RATE)
		plot (x,data[0],'ro')
		plot (x,data[1],'bo')
		show ()

	
	a = np.sum(data[0])/NUMBER_OF_SAMPLES
	ionpump = math.exp(a * 1000 * 0.124) * 2.9741e-9
	
	a = np.sum(data[1])/NUMBER_OF_SAMPLES
	turbo_temp = (a-0.4)/0.0195

	return(ionpump,turbo_temp)
	
if __name__ == "__main__":
	print readPressureAndTemperature(True)