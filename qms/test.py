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
qmg.comm('RAN 5')
qms = qms.qms(qmg, sql_queue)

print qms.emission_status(turn_on = True)

print qms.sem_status(turn_on = True)

qms.mass_scan()

time.sleep(10) # Allow time for the sql_saver to empty

#print qmg.comm('RSC')

#print qmg.comm('RDE')

#print qmg.comm('RAU')

#print qmg.comm('RDE')
