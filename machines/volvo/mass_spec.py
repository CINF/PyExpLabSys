# pylint: disable=R0913,W0142,C0103

""" Mass spec program for Volvo """

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
chamber = 'dummy'
#chamber = 'volvo'                                                                        

qms = ms.qms(qmg, sql_queue, chamber=chamber, credentials=sql_credentials.username)
qmg.reverse_range = False
printer = qmg_status_output.qms_status_output(qms, sql_saver_instance=sql_saver)
printer.start()

if False:
    channel_list = qms.read_ms_channel_list('channel_list.txt')
    meta_udp = qmg_meta_channels.udp_meta_channel(qms, timestamp, channel_list, 5)
    meta_udp.daemon = True
    meta_udp.start()
    print qms.mass_time(channel_list['ms'], timestamp)

if True:
    qms.mass_scan(26, 8, comment='qmg421 -8', amp_range=-8)
    qms.mass_scan(26, 8, comment='qmg421 -9', amp_range=-9)
    qms.mass_scan(26, 8, comment='qmg421 -10', amp_range=-10)
    qms.mass_scan(26, 8, comment='qmg421 -11', amp_range=-11)
    qms.mass_scan(26, 8, comment='qmg421 -12', amp_range=-12)

time.sleep(1)
printer.stop()
