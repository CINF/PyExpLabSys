# pylint: disable=R0913,W0142,C0103

""" Mass spec program for microreactor """

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

qmg = qmg420.qmg_420()
qms = ms.qms(qmg, sql_queue)

qms.chamber = 'microreactor' #Uncomment this to save data in correct db

qms.communication_mode(computer_control=True)
channel_list = qms.read_ms_channel_list('channel_list.txt')
printer = qmg_status_output.qms_status_output(qms, sql_saver_instance=sql_saver)
printer.daemon = True
printer.start()

"""
meta_udp = qmg_meta_channels.udp_meta_channel(qms, timestamp, channel_list, 5)
meta_udp.daemon = True
meta_udp.start()


meta_flow = qmg_meta_channels.compound_udp_meta_channel(qms, timestamp, channel_list['ms'][0]['comment'], 5, 'rasppi27', 9999, 'read_flows')
meta_flow.create_channel('Sample Pressure', 0)
meta_flow.create_channel('Flow1, O2', 1)
meta_flow.create_channel('Flow2, D2', 2)
meta_flow.create_channel('Flow3, He', 3)
meta_flow.create_channel('Flow4, H2', 4)
meta_flow.daemon = True
meta_flow.start()
"""

qms.mass_scan(0, 50, comment = 'Testing position of Hydrogen and Deuterium')
#print qms.mass_time(channel_list['ms'], timestamp)

time.sleep(1)
printer.stop()

#print qmg.read_voltages()
#print qmg.sem_status(voltage=1800, turn_on=True)
#print qmg.emission_status(current=0.1,turn_on=True)
#print qmg.qms_status()
