# pylint: disable=R0913,W0142,C0103

""" Mass spec program for Parallel Screening """

import Queue
import sys
import time

sys.path.append('../../')
import SQL_saver

sys.path.append('../../qms/')
import qms as ms
import qmg420
import qmg_status_output
import qmg_meta_channels

import sql_credentials

timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
sql_queue = Queue.Queue()
sql_saver = SQL_saver.sql_saver(sql_queue, sql_credentials.username)
sql_saver.daemon = True
sql_saver.start()

qmg = qmg420.qmg_420(switch_range=True)
# This mass spec had a wrong order of range 9 and 11
qms = ms.qms(qmg, sql_queue)

qms.chamber = 'ps' #Uncomment this to save data in correct db
qms.sql_credentials = sql_credentials.username

qms.communication_mode(computer_control=True)

channel_list = qms.read_ms_channel_list('channel_list.txt')
print channel_list

printer = qmg_status_output.qms_status_output(qms, sql_saver_instance=sql_saver)
printer.daemon = True
printer.start()

meta_udp = qmg_meta_channels.udp_meta_channel(qms, timestamp, channel_list, 5)
meta_udp.daemon = True
meta_udp.start()

print qms.mass_time(channel_list['ms'], timestamp)

time.sleep(1)
printer.stop()

#print qmg.read_voltages()
#print qmg.sem_status(voltage=1800, turn_on=True)
#print qmg.emission_status(current=0.1,turn_on=True)
#print qmg.qms_status()

