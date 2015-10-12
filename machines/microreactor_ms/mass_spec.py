# pylint: disable=R0913,W0142,C0103

""" Mass spec program for Microreactor """

import Queue
import time
import logging
import PyExpLabSys.common.sql_saver as sql_saver
import PyExpLabSys.drivers.pfeiffer_qmg422 as qmg422
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

qmg = qmg422.qmg_422(port='/dev/ttyS0', speed=9600)
chamber = 'microreactor'
#chamber = 'dummy'

qms = ms.qms(qmg, sql_queue, chamber=chamber, credentials=sql_credentials.username)
qmg.reverse_range = True
printer = qmg_status_output.qms_status_output(qms, sql_saver_instance=sql_saver)
printer.start()

if True:
    channel_list = qms.read_ms_channel_list('channel_list.txt')
    meta_udp = qmg_meta_channels.udp_meta_channel(qms, timestamp, channel_list, 5)
    meta_udp.daemon = True
    meta_udp.start()
    print qms.mass_time(channel_list['ms'], timestamp)

if False:
    qms.mass_scan(0, 50, comment='Testing mass position', amp_range=-7)

if False:
    print qmg.sem_status(voltage=1800, turn_on=True)
    print qmg.emission_status(current=0.1, turn_on=True)

time.sleep(1)
printer.stop()

