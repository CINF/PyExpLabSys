""" Mass spec program """
from __future__ import print_function
import os
import sys
import time
try:
    import Queue as queue
except ImportError:
    import queue
import PyExpLabSys.common.database_saver as database_saver
import PyExpLabSys.drivers.pfeiffer_qmg420 as qmg420
import PyExpLabSys.drivers.pfeiffer_qmg422 as qmg422
import PyExpLabSys.apps.qms.qms as ms
import PyExpLabSys.apps.qms.qmg_status_output as qmg_status_output
import PyExpLabSys.apps.qms.qmg_meta_channels as qmg_meta_channels
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.utilities import activate_library_logging
from PyExpLabSys.common.supported_versions import python2_and_3
BASEPATH = os.path.abspath(__file__)[:os.path.abspath(__file__).find('PyExpLabSys')]
sys.path.append(BASEPATH + '/PyExpLabSys/machines/' + sys.argv[1])
import settings # pylint: disable=F0401
python2_and_3(__file__)

LOGGER = get_logger('Mass Spec', level='info', file_log=True,
                    file_name='qms.txt', terminal_log=False,
                    email_on_warnings=False, email_on_errors=False,
                    file_max_bytes=104857600, file_backup_count=5)

activate_library_logging('PyExpLabSys.drivers.pfeiffer_qmg422', logger_to_inherit_from=LOGGER)
activate_library_logging('PyExpLabSys.apps.qms.qms', logger_to_inherit_from=LOGGER)

class MassSpec(object):
    """ User interface to mass spec code """
    def __init__(self):
        sql_queue = queue.Queue()
        self.data_saver = database_saver.SqlSaver(settings.username,
                                                  settings.username, sql_queue)
        self.data_saver.start()
        if settings.qmg == '420':
            self.qmg = qmg420.qmg_420(settings.port)
        if settings.qmg == '422':
            print(settings.port)
            self.qmg = qmg422.qmg_422(port=settings.port, speed=settings.speed)

        livesocket = LiveSocket(settings.name + '-mass-spec', ['qms-value'])
        livesocket.start()

        self.qms = ms.QMS(self.qmg, sql_queue, chamber=settings.chamber,
                          credentials=settings.username, livesocket=livesocket)
        self.qmg.reverse_range = settings.reverse_range
        self.printer = qmg_status_output.qms_status_output(self.qms,
                                                           sql_saver_instance=self.data_saver)
        self.printer.start()

    def __del__(self):
        self.printer.stop()

    def sem_and_filament(self, turn_on=False, voltage=1800):
        """ Turn on and off the mas spec """
        if turn_on is True:
            self.qmg.sem_status(voltage=voltage, turn_on=True)
            self.qmg.emission_status(current=0.1, turn_on=True)
        else:
            self.qmg.sem_status(voltage=1800, turn_off=True)
            self.qmg.emission_status(current=0.1, turn_off=True)

    def leak_search(self):
        """ Do a mass time scan on mass 4 """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        channel_list = {}
        channel_list['ms'] = {}
        channel_list['ms'][0] = {'comment': 'Leak Search', 'autorange':False}
        channel_list['ms'][1] = {'masslabel': 'He', 'speed':10, 'mass':4, 'amp_range':9}
        self.qms.mass_time(channel_list['ms'], timestamp, no_save=True)

    def mass_time_scan(self, channel_list='channel_list'):
        """ Perform a mass-time scan """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        qms_channel_list = self.qms.read_ms_channel_list(BASEPATH + '/PyExpLabSys/machines/' +
                                                         sys.argv[1] + '/channel_lists/' +
                                                         channel_list + '.txt')
        meta_udp = qmg_meta_channels.udp_meta_channel(self.qms, timestamp, qms_channel_list, 5)
        meta_udp.daemon = True
        meta_udp.start()
        self.qms.mass_time(qms_channel_list['ms'], timestamp)

    def mass_scan(self, start_mass=0, scan_width=100, comment='bg_scan', amp_range=0):
        """ Perform mass scan """
        self.qms.mass_scan(start_mass, scan_width, comment, amp_range)
        time.sleep(1)

if __name__ == '__main__':
    MS = MassSpec()
    #MS.sem_and_filament(True, 1800)
    #time.sleep(10)
    #MS.leak_search()

    MS.mass_time_scan()
    #MS.mass_scan(0, 50, 'Background scan', amp_range=0)
    #MS.mass_scan(0, 50, 'Background scan -11', amp_range=-11)
    #MS.mass_scan(0, 50, 'Background scan -9', amp_range=-9)
    #MS.mass_scan(0, 50, 'Background scan -7', amp_range=-7)
