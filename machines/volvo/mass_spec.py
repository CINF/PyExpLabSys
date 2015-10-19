""" Mass spec program for Volvo """

import Queue
import time
import PyExpLabSys.common.sql_saver as sql_saver
import PyExpLabSys.drivers.pfeiffer_qmg422 as qmg422
import PyExpLabSys.apps.qms.qms as ms
import PyExpLabSys.apps.qms.qmg_status_output as qmg_status_output
import PyExpLabSys.apps.qms.qmg_meta_channels as qmg_meta_channels
from PyExpLabSys.common.utilities import get_logger
import sql_credentials

LOGGER = get_logger('Mass Spec', level='info', file_log=True,
                    file_name='qms.txt', terminal_log=False)

def main():
    """ Main mass main loop """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    sql_queue = Queue.Queue()
    data_saver = sql_saver.SqlSaver(sql_queue, sql_credentials.username)
    data_saver.start()

    qmg = qmg422.qmg_422(port='/dev/ttyS0', speed=9600)
    chamber = 'dummy'
    #chamber = 'volvo'

    qms = ms.QMS(qmg, sql_queue, chamber=chamber, credentials=sql_credentials.username)
    qmg.reverse_range = False

    printer = qmg_status_output.qms_status_output(qms, sql_saver_instance=data_saver)
    printer.start()

    if True:
        channel_list = qms.read_ms_channel_list('channel_list.txt')
        meta_udp = qmg_meta_channels.udp_meta_channel(qms, timestamp, channel_list, 5)
        meta_udp.daemon = True
        meta_udp.start()
        print qms.mass_time(channel_list['ms'], timestamp)

    if False:
        qms.mass_scan(26, 8, comment='Background scan', amp_range=-11)


        time.sleep(1)
        printer.stop()

    if False: # here filament and sem can be modified
        print qmg.sem_status(voltage=1800, turn_on=True)
        print qmg.emission_status(current=0.1,turn_on=True)

if __name__ == '__main__':
    main()
            
