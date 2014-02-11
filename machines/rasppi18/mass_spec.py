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

sql_queue = Queue.Queue()
sql_saver = SQL_saver.sql_saver(sql_queue,sql_credentials.username)
sql_saver.daemon = True
sql_saver.start()

qmg = qmg422.qmg_422()
qms = ms.qms(qmg, sql_queue)


#qms.chamber = 'stm312' #Uncomment this to save data in correct db


qms.communication_mode(computer_control=True)
printer = qmg_status_output.qms_status_output(qms,sql_saver_instance=sql_saver)
printer.daemon = True
printer.start()

#qms.mass_scan(0,50,comment = 'Test scan - qgm422')


channel_list = {}
channel_list[0] = {'comment':'leaktesting','autorange':True}
#channel_list[1] = {'mass':1.6,'speed':9, 'masslabel':'M2'}
channel_list[1] = {'mass':4,'speed':9, 'masslabel':'M4', 'amp_range':6}
channel_list[2] = {'mass':7,'speed':9, 'masslabel':'M7', 'amp_range':6}
#channel_list[4] = {'mass':11.4,'speed':9, 'masslabel':'M12'}
#channel_list[5] = {'mass':13.4,'speed':9, 'masslabel':'M14'}
#channel_list[6] = {'mass':17.4,'speed':9, 'masslabel':'M18'}
#channel_list[1] = {'mass':27,'speed':9, 'masslabel':'M27'}
#channel_list[8] = {'mass':31.4,'speed':9, 'masslabel':'M32'}
#channel_list[9] = {'mass':43.4,'speed':9, 'masslabel':'M44'}"""
#channel_list[2] = {'mass':28,'speed':9,'masslabel':'M28'}
#channel_list[3] = {'mass':29,'speed':9,'masslabel':'M29'}


timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
#meta_udp = qmg_meta_channels.udp_meta_channel(qmg, timestamp, channel_list[0]['comment'], 5)
#meta_udp.create_channel('Temperature', 'rasppi19', 9990, 'read_global_temp')
#meta_udp.create_channel('Chamber pressure', 'rasppi19', 9990, 'read_global_pressure')
#meta_udp.create_channel('HPC, Temperature', 'rasppi19', 9990, 'read_hp_temp')
#meta_udp.create_channel('HPC, Pirani', 'rasppi13', 9999, 'read_pirani')
#meta_udp.create_channel('HPC, Pressure Controller', 'rasppi13', 9999, 'read_pressure')
#meta_udp.daemon = True
#meta_udp.start()

print qms.mass_time(channel_list, timestamp)

time.sleep(1)
printer.stop()

#print qmg.read_voltages()
#print qmg.sem_status(voltage=2200, turn_on=True)
#print qmg.emission_status(current=0.1,turn_on=True)
#print qmg.qms_status()
