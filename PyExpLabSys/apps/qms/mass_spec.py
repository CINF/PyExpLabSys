""" Mass spec program for Volvo """
import os
import sys
import time
import Queue
import PyExpLabSys.common.database_saver as database_saver
import PyExpLabSys.drivers.pfeiffer_qmg420 as qmg420
import PyExpLabSys.drivers.pfeiffer_qmg422 as qmg422
import PyExpLabSys.apps.qms.qms as ms
import PyExpLabSys.apps.qms.qmg_status_output as qmg_status_output
import PyExpLabSys.apps.qms.qmg_meta_channels as qmg_meta_channels
from PyExpLabSys.common.utilities import get_logger
BASEPATH = os.path.abspath(__file__)[:os.path.abspath(__file__).find('PyExpLabSys')]
sys.path.append(BASEPATH + '/PyExpLabSys/machines/' + sys.argv[1])
import settings # pylint: disable=F0401

LOGGER = get_logger('Mass Spec', level='info', file_log=True,
                    file_name='qms.txt', terminal_log=False)

class MassSpec(object):
    """ User interface to mass spec code """
    def __init__(self):
        sql_queue = Queue.Queue()
        self.data_saver = database_saver.SqlSaver(settings.username, settings.username, sql_queue)
        self.data_saver.start()
        if settings.qmg == '420':
            self.qmg = qmg420.qmg_420(settings.port)
        if settings.qmg == '422':
            print settings.port
            self.qmg = qmg422.qmg_422(port=settings.port, speed=settings.speed)
        self.qms = ms.QMS(self.qmg, sql_queue, chamber=settings.chamber,
                          credentials=settings.username)
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

    def mass_time_scan(self):
        """ Perform a mass-time scan """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        channel_list = self.qms.read_ms_channel_list(BASEPATH + '/PyExpLabSys/machines/' +
                                                     sys.argv[1] + '/channel_list.txt')
        meta_udp = qmg_meta_channels.udp_meta_channel(self.qms, timestamp, channel_list, 5)
        meta_udp.daemon = True
        meta_udp.start()
        self.qms.mass_time(channel_list['ms'], timestamp)

    def mass_scan(self, start_mass=0, scan_width=50):
        """ Perform mass scan """
        self.qms.mass_scan(start_mass, scan_width, comment='Background scan', amp_range=-9)
        time.sleep(1)

if __name__ == '__main__':
    MS = MassSpec()
    #MS.sem_and_filament(turn_on=True, voltage=2800)
    #MS.leak_search()
    #MS.mass_scan(0, 50)
    MS.mass_time_scan()


