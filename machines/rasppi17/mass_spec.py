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

qms.chamber = 'microreactorNG' #Uncomment this to save data in correct db
qms.communication_mode(computer_control=True)

channel_list = qms.read_ms_channel_list('channel_list.txt')

printer = qmg_status_output.qms_status_output(qms,sql_saver_instance=sql_saver)
printer.daemon = True
printer.start()

meta_udp = qmg_meta_channels.udp_meta_channel(qms, timestamp, channel_list, 5)
meta_udp.daemon = True
meta_udp.start()

meta_flow = qmg_meta_channels.compound_udp_meta_channel(qms, timestamp, channel_list['ms'][0]['comment'],5,'rasppi16',9998, 'read_all')
meta_flow.create_channel('Sample Pressure',0)
meta_flow.create_channel('Flow, O2',1)
meta_flow.create_channel('Flow, CO2',2)
meta_flow.create_channel('Flow, H2',4)
meta_flow.create_channel('Flow, Ar',5)
meta_flow.create_channel('Flow, CO',6)
meta_flow.daemon = True
meta_flow.start()

#qms.mass_scan(0,100,comment = 'Leak testing Ar')

print qms.mass_time(channel_list['ms'], timestamp)

#time.sleep(1)
printer.stop()

if False: # here filament and sem can be modified
    print qmg.sem_status(voltage=1600, turn_on=True)
    print qmg.emission_status(current=0.1,turn_on=True)

