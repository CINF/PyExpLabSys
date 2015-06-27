# pylint: disable=C0103
""" Mass-spec settings for STM312 """

import Queue
import time
import logging
import PyExpLabSys.common.sql_saver as sql_saver
import PyExpLabSys.drivers.pfeiffer_qmg420 as qmg420
import PyExpLabSys.apps.qms.qms as ms
import PyExpLabSys.apps.qms.qmg_status_output as qmg_status_output
import PyExpLabSys.apps.qms.qmg_meta_channels as qmg_meta_channels
import sql_credentials

logging.basicConfig(filename="qms.txt", level=logging.ERROR)
logging.basicConfig(level=logging.DEBUG)

timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
sql_queue = Queue.Queue()
sql_saver = sql_saver.SqlSaver(sql_queue, sql_credentials.username)
sql_saver.start()

qmg = qmg420.qmg_420()
chamber = 'dummy'
#chamber = 'stm312'
qms = ms.qms(qmg, sql_queue, chamber=chamber, credentials=sql_credentials.username)

printer = qmg_status_output.qms_status_output(qms, sql_saver_instance=sql_saver)
printer.start()

if True:
    channel_list = qms.read_ms_channel_list('channel_list.txt')
    meta_udp = qmg_meta_channels.udp_meta_channel(qms, timestamp, channel_list, 5)
    meta_udp.daemon = True
    meta_udp.start()
    print qms.mass_time(channel_list['ms'], timestamp)

if False:
    # for choosing between mass time and mass scan
    qms.mass_scan(0, 10, comment='TEST qmg420 stm312')

time.sleep(1)
printer.stop()

# for turning on or off the filament and SEM
if False:
    print qmg.sem_status(voltage=1500, turn_on=True)
    print qmg.emission_status(current=0.1, turn_on=True)
    print qmg.emission_status()
elif False:
    print qmg.sem_status(voltage=1800, turn_off=True)
    print qmg.emission_status(current=0.1, turn_off=True)

"""
print 'Status - ESQ'
print qmg.comm('ESQ')
esq = qmg.comm('ESQ')
esq = int(esq[:esq.find(',')])
print bin(esq)
print 'Emission on: ' + bin(esq)[-3]
print 'SEM on: ' + bin(esq)[-4]
"""



"""
print '---'
print '--'
print qmg.comm('ECU') # Emission current, 0 to 20A
print '---'
print qmg.comm('QHW') # Ion source
print '---'
print 'These values needs to go in a config-file:'
print qmg.comm('SQA') # Type of analyzer, 0: 125, 1: 400, 4:200
print '---'
print qmg.comm('SMR') # Mass-range, this needs to go in a config-file
print '---'
print qmg.comm('SDT') # Detector type
print '---'
print qmg.comm('SIT') # Ion source

print qmg.comm('TSI, 0')# 1: Simulation, 0: real data
"""
