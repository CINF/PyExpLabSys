import qms
import qmg420

import Queue
import sys
import time

sys.path.append('../')
import SQL_saver

sql_queue = Queue.Queue()
sql_saver = SQL_saver.sql_saver(sql_queue,'dummy')
sql_saver.daemon = True
sql_saver.start()

qmg = qmg420.qmg_420()
qms = qms.qms(qmg, sql_queue)
print qms.emission_status(turn_on = True)
print qms.sem_status(turn_on = True)

for i in range(0,64):
    qmg.config_channel(i,18,10,'no')

qmg.config_channel(1,mass=18,speed=10,amp_range=5,enable='yes')
qmg.config_channel(2,mass=28,speed=10,amp_range=5,enable='yes')
qmg.config_channel(3,mass=32,speed=2,amp_range=5,enable='yes')
qmg.config_channel(4,mass=32,speed=2,amp_range=5,enable='yes')
qmg.config_channel(5,mass=32,speed=2,amp_range=5,enable='yes')
qmg.config_channel(6,mass=28,speed=10,amp_range=5,enable='yes')
qmg.config_channel(7,mass=44,speed=10,amp_range=5,enable='yes')

qmg.comm('RUN')
for i in range(0,25):
    time.sleep(0.5)
    #print qmg.comm('STW')[6] == '0'
    length = int(qmg.comm('RBC'))
    header = qmg.comm('HEA')
    if length > 2:
        value = qmg.comm(chr(5))
    else:
        value = ""
    print 'Length: ' + str(length) + ',  Header: ' + header + ', Value: ' + value
    
#qmg.comm('SYN 1') #Power line supression

#qmg.comm('RAN 5')
#qms = qms.qms(qmg, sql_queue)
#print qms.emission_status(turn_on = True)
#print qms.sem_status(turn_on = True)

#qms.mass_scan(0, 20)

#time.sleep(2) # Allow time for the sql_saver to empty

#print qmg.comm('RSC')

#print qmg.comm('RDE')

#print qmg.comm('RAU')

#print qmg.comm('RDE')
