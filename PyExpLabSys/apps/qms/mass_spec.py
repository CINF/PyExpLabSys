# pylint: disable=no-member
""" Mass spec program """
from __future__ import print_function
import os
import sys
import time
import datetime
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
from PyExpLabSys.common.sockets import LiveSocket, DateDataPullSocket
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.common.utilities import activate_library_logging
from PyExpLabSys.common.supported_versions import python2_and_3
BASEPATH = os.path.abspath(__file__)[:os.path.abspath(__file__).find('PyExpLabSys')]
sys.path.append(BASEPATH + '/PyExpLabSys/machines/' + sys.argv[1])
import settings # pylint: disable=wrong-import-position
python2_and_3(__file__)

LOGGER = get_logger('Mass Spec', level='warning', file_log=True,
                    file_name='qms.txt', terminal_log=False,
                    email_on_warnings=False, email_on_errors=False,
                    file_max_bytes=104857600, file_backup_count=5)

activate_library_logging('PyExpLabSys.drivers.pfeiffer_qmg422',
                         logger_to_inherit_from=LOGGER)
activate_library_logging('PyExpLabSys.apps.qms.qmg_status_output',
                         logger_to_inherit_from=LOGGER)
activate_library_logging('PyExpLabSys.apps.qms.qmg_meta_channels',
                         logger_to_inherit_from=LOGGER)
activate_library_logging('PyExpLabSys.apps.qms.qms',
                         logger_to_inherit_from=LOGGER)

try:
    from local_channels import Local
    LOCAL_READER = Local()
    LOCAL_READER.daemon = True
    LOCAL_READER.start()
except ImportError:
    pass


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

        try:
            livesocket = LiveSocket(settings.name + '-mass-spec', ['qms-value'])
            livesocket.start()
        except:
            livesocket = None

        pullsocket = DateDataPullSocket(settings.name + '-mass-spec', ['qms-value'])
        pullsocket.start()

        self.qms = ms.QMS(self.qmg, sql_queue, chamber=settings.chamber,
                          credentials=settings.username, livesocket=livesocket,
                          pullsocket=pullsocket)
        self.qmg.reverse_range = settings.reverse_range
        self.printer = qmg_status_output.QmsStatusOutput(self.qms,
                                                         sql_saver_instance=self.data_saver)
        self.printer.start()

    def sem_and_filament(self, turn_on=False, voltage=1800):
        """ Turn on and off the mas spec """
        if turn_on is True:
            self.qmg.sem_status(voltage=voltage, turn_on=True)
            self.qmg.emission_status(current=0.1, turn_on=True)
        else:
            self.qmg.sem_status(voltage=1800, turn_off=True)
            self.qmg.emission_status(current=0.1, turn_off=True)

    def leak_search(self, speed=10):
        """ Do a mass time scan on mass 4 """
        timestamp = datetime.datetime.now()
        channel_list = {}
        channel_list['ms'] = {}
        channel_list['ms'][0] = {'comment': 'Leak Search', 'autorange':False,
                                 'mass-scan-interval':999999999}
        channel_list['ms'][1] = {'masslabel': 'He', 'speed':speed, 'mass':4, 'amp_range':9}
        self.qms.mass_time(channel_list['ms'], timestamp, no_save=True)

    def mass_time_scan(self, channel_list='channel_list'):
        """ Perform a mass-time scan """
        timestamp = datetime.datetime.now()
        qms_channel_list = self.qms.read_ms_channel_list(BASEPATH + '/PyExpLabSys/machines/' +
                                                         sys.argv[1] + '/channel_lists/' +
                                                         channel_list + '.txt')
        meta_udp = qmg_meta_channels.MetaChannels(self.qms, timestamp, qms_channel_list)
        meta_udp.daemon = True
        meta_udp.start()
        self.printer.meta_channels = meta_udp
        self.qms.mass_time(qms_channel_list['ms'], timestamp)

    def mass_scan(self, start_mass=0, scan_width=100, comment='bg_scan', amp_range=0):
        """ Perform mass scan """
        self.qms.mass_scan(start_mass, scan_width, comment, amp_range)
        time.sleep(1)

    def sleep(self, duration):
        """ Sleep for a while and print output """
        msg = 'Sleeping for {} seconds..'
        for i in range(duration, 0, -1):
            self.qms.operating_mode = msg.format(i)
            time.sleep(1)
        self.qms.operating_mode = 'Idling'

if __name__ == '__main__':
    try:
        # Initialize QMS
        MS = MassSpec()
        MS.sem_and_filament(True, 1800)
        MS.sleep(10)

        # Choose and start measurement(s)
        MS.leak_search(speed=8)

        #MS.mass_time_scan()

        #MS.mass_scan(0, 50, 'flow6', amp_range=-11)
        #MS.mass_scan(0, 50, 'After power line cleanup', amp_range=-11)

        #MS.mass_scan(0, 50, 'Background scan -11', amp_range=-11)
        #MS.mass_scan(0, 50, 'Background scan -9', amp_range=-9)
        #MS.mass_scan(0, 50, 'Background scan -7', amp_range=-7)
    except:
        MS.printer.stop()
        raise
    finally:
        MS.printer.stop()
