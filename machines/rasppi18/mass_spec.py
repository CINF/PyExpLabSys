import Queue
import sys
import time

sys.path.append('../../')
import SQL_saver

sys.path.append('../../qms')
import qms as ms
import qmg422
import qmg_status_output
import qmg_meta_channels

import sql_credentials

timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
sql_queue = Queue.Queue()
sql_saver = SQL_saver.sql_saver(sql_queue,sql_credentials.username)
sql_saver.daemon = True
sql_saver.start()

qmg = qmg422.qmg_422()
qms = ms.qms(qmg, sql_queue)


qms.chamber = 'stm312' #Uncomment this to save data in correct db
qms.communication_mode(computer_control=True)
printer = qmg_status_output.qms_status_output(qms, sql_saver_instance=sql_saver)
printer.daemon = True
printer.start()
if False:
    channel_list = qms.read_ms_channel_list('channel_list.txt')
    #printer = qmg_status_output.qms_status_output(qms, sql_saver_instance=sql_saver)
    #printer.daemon = True
    #printer.start()
    
    meta_udp = qmg_meta_channels.udp_meta_channel(qms, timestamp, channel_list, 5)
    meta_udp.daemon = True
    meta_udp.start()
if True:
    # for choosing between mass time and mass scan
    qms.mass_scan(0, 100, comment='Test')#Chamber background,P=9.7E-11torr')
#print qms.mass_time(channel_list['ms'], timestamp)

time.sleep(1)
printer.stop()

# for turning on or off the filament and SEM
if False:
    print qmg.sem_status(voltage=2200, turn_on=True)
    print qmg.emission_status(current=0.1, turn_on=True)

