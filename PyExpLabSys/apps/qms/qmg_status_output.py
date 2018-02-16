""" Text UI for mass spec program """
import threading
import logging
import curses
import time
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
LOGGER.addHandler(logging.NullHandler())

class QmsStatusOutput(threading.Thread):
    """ Text UI for mass spec program """
    def __init__(self, qms_instance, sql_saver_instance=None, meta_channel_instance=None):
        threading.Thread.__init__(self)
        self.daemon = True

        self.qms = qms_instance
        if not sql_saver_instance is None:
            self.sql = sql_saver_instance
        else:
            self.sql = None
        self.meta_channels = meta_channel_instance
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)

    def run(self):
        while True:
            self.screen.addstr(1, 1, self.qms.operating_mode)

            if self.qms.operating_mode == "Mass Time":
                timestamp = "Timestamp: " + self.qms.current_timestamp
                self.screen.addstr(3, 1, timestamp)
                runtime = "Experiment runtime: {0:.1f}s".format(self.qms.measurement_runtime)
                self.screen.addstr(4, 1, runtime)
                qsize = "Queue length: {0:.0f} items".format(self.sql.queue.qsize())
                self.screen.addstr(5, 1, qsize)
                self.screen.clrtoeol()

                #self.screen.addstr(5,20, self.qms.channel_list[0]['comment'])
                self.screen.addstr(7, 1, 'QMS-channels')
                for i in range(1, len(self.qms.channel_list) + 1):
                    channel = self.qms.channel_list[i]
                    self.screen.addstr(8+i, 1, channel['masslabel'] + ': ' +
                                       channel['value'] + '                 ')

                self.screen.addstr(7, 30, 'Meta-channels')
                if self.meta_channels is None:
                    self.screen.addstr(9, 30, 'No access to meta-channels')
                else:
                    for i in range(0, len(self.meta_channels.channels)):
                        channel = self.meta_channels.channels[i]
                        self.screen.addstr(9 + i, 30, channel.channel_data['label'] +
                                           ': ' + str(channel.channel_data['value']) +
                                           '                ')

            if self.qms.operating_mode == 'Mass-scan':
                self.screen.addstr(2, 1, self.qms.message)
                timestamp = "Timestamp: " + self.qms.current_timestamp
                self.screen.addstr(3, 1, timestamp)
                runtime = "Experiment runtime: {0:.1f}s".format(self.qms.measurement_runtime)
                self.screen.addstr(4, 1, runtime)
                self.screen.addstr(5, 1, 'Current action: ' + self.qms.current_action)
                self.screen.clrtoeol()



            if not self.sql is None:
                commits = "SQL commits: {0:.0f}".format(self.sql.commits)
                self.screen.addstr(3, 40, commits)
                commit_time = "Last commit duration: {0:.1f}".format(self.sql.commit_time)
                self.screen.addstr(4, 40, commit_time)

            key_value = self.screen.getch()
            if key_value == ord('q'):
                self.qms.stop = True

            self.screen.refresh()
            time.sleep(1)

    def stop(self):
        """ Stop and cleanup """
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()
