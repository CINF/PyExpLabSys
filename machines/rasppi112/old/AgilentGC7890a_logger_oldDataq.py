from PyExpLabSys.drivers.dataq_comm import DataQ
import time
import os
from GC_relay_control import init_GC, start_GC

if os.path.isdir('dat') is not True:
	os.mkdir('dat')

DATAQ = DataQ('/dev/ttyACM0')
for n in [1,2,3,4]: #1 is ready, #3 is FID, #4 is TCD
	DATAQ.add_channel(n)
DATAQ.start_measurement()

init_GC()

script_start_time = time.ctime()
path = 'dat/'+script_start_time
os.mkdir(path)

print('Experiment started on '+script_start_time)

start_time = time.time()
injection_number = 0
last_injection = 1
while True: #I know, it doesn't look nice
	read_out = DATAQ.read_measurements()
	if read_out[1] > 2.2: #ready is 3.3 volt (high true), false is 0.4 volt
		start_GC() #there is no stop
		injection_time = time.ctime()
		injection_number = injection_number+1
		injection_start_time = time.time()
		print('Injection number '+str(injection_number)
			+' started '+str((round(injection_start_time-start_time)/60))+' mins into the experiment on '+injection_time)
		rel_time = []
		raw_data = []
		while (time.time()-injection_start_time) < 800: #spectrum time
			raw_data.append(DATAQ.read_measurements())
			rel_time.append(time.time()-injection_start_time)
		FID_file = open(path+'/'+str(injection_number)+'_FID.txt','w+') #write data to file
		FID_file.write('#injection abs time: '+str(injection_time)+'\n')
		FID_file.write('#injection rel time: '+str(injection_start_time-start_time)+'\n')
		FID_file.write('#injection number: '+str(injection_number)+'\n')
		TCD_file = open(path+'/'+str(injection_number)+'_TCD.txt','w+')
		TCD_file.write('#injection abs time: '+str(injection_time)+'\n')
		TCD_file.write('#injection rel time: '+str(injection_start_time-start_time)+'\n')
		TCD_file.write('#injection number: '+str(injection_number)+'\n')
		for n in range(0,len(rel_time)):
			FID_file.write(str(rel_time[n])+'    '+str(raw_data[n][3])+'\n')
			TCD_file.write(str(rel_time[n])+'    '+str(raw_data[n][4])+'\n')
		FID_file.close()
		TCD_file.close()
		print('Data from injection '+str(injection_number)+' written to file')
	if injection_number == last_injection: #number of total injections
		DATAQ.stop_measurement()
		print('Experiment ended on '+time.ctime())
		break
	time.sleep(1) #it only checks every second, wether it is ready

