"""Measure values from omicron's two PVCi's (ion gauge controllers), log to database and set on live socket server"""

from __future__ import print_function
from time import sleep
import threading
import curses

from PyExpLabSys.common.sockets import LiveSocket, DateDataPullSocket
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.value_logger import LoggingCriteriumChecker
from PyExpLabSys.common.utilities import get_logger
from PyExpLabSys.drivers import epimax

import credentials

# Wait time in seconds between serial communications
WAIT = 0.25

# codename : (address, key)
CODENAME_TRANSLATION = {
    'omicron_ana_pressure': (2, 'ion_gauge_1_pressure'),
    'omicron_prep_pressure': (1, 'ion_gauge_1_pressure'),
    'omicron_roughing_2_prep': (1, 'slot_a_value_1'),
    'omicron_roughing_1_ana': (2, 'slot_a_value_1'),
    'omicron_roughing_3_diff': (2, 'slot_b_value_1'),
    }

EXTRA_LIVE = {
    }
LOG = get_logger('pvci_monitor', level='warning')

class ValuePrinter(threading.Thread):
    """Print values nicely in terminal"""

    def __init__(self, logger):
        """Initialize"""
        threading.Thread.__init__(self)
        self.logger = logger
        self.values = dict(self.logger.values)
        self.printing = True

        self.screen = curses.initscr()
        self.win = curses.newwin(10, 50, 0, 0)
        curses.cbreak()
        curses.noecho()
        curses.halfdelay(1)

    def stop(self):
        """Exit nicely"""
        self.printing = False
        sleep(1)
        self.screen.keypad(0)
        curses.nocbreak()
        curses.echo()
        curses.endwin()

    def run(self):
        """Print values to screen"""
        while self.printing:
            try:
                char = self.screen.getch()
                if char == ord('q'):
                    self.logger.stop()
                    self.stop()
                    break
                self.update_screen()
                sleep(0.1)
            except KeyboardInterrupt:
                self.stop()
                break

    def update_screen(self):
        """Update screen information"""
        try:
            if self.values != self.logger.values:
                self.values = dict(self.logger.values)
                # Print header
                self.win.addstr(0, 0, 'Omicron Pressure Logger running.')
                self.win.addstr(1, 10, '(Quit with "q")')

                # Print body
                self.win.addstr(3, 0, 'Chamber pressures')
                string = 'Prep pressure: {} mbar'.format(self.values['omicron_prep_pressure'])
                self.win.addstr(4, 3, string.ljust(50))
                string = 'Ana pressure : {} mbar'.format(self.values['omicron_ana_pressure'])
                self.win.addstr(5, 3, string.ljust(50))

                self.win.addstr(6, 0, 'Roughing lines')
                string = 'Prep : {} mbar'.format(self.values['omicron_roughing_2_prep'])
                self.win.addstr(7, 3, string.ljust(40))
                string = 'Ana  : {} mbar'.format(self.values['omicron_roughing_1_ana'])
                self.win.addstr(8, 3, string.ljust(40))
                string = 'Diff : {} mbar'.format(self.values['omicron_roughing_3_diff'])
                self.win.addstr(9, 3, string.ljust(40))
                self.win.refresh()
            else:
                if not self.logger.is_alive():
                    self.stop()
                    print('Logger not running..')
        except: # This is not handled well
            self.stop()

class DataLogger(threading.Thread):
    """Thread to continuously log pressures."""

    def __init__(self, pvci, live_socket, pullsocket, database_saver, criterium_checker):
        """Initialize"""
        threading.Thread.__init__(self)
        self.pvci = pvci
        self.live_socket = live_socket
        self.pullsocket = pullsocket
        self.database_saver = database_saver
        self.criterium_checker = criterium_checker

        self.values = {}
        for codename in CODENAME_TRANSLATION.keys():
            self.values[codename] = 0
        self.loop = True

    def stop(self):
        """Exit nicely"""
        self.loop = False

    def run(self):
        """Measure and log """
        # Main loop
        quit = False
        while not quit:
            for codename, (address, key) in CODENAME_TRANSLATION.items():
                if self.loop:
                    sleep(WAIT)
                    self.pvci.address = address
                    value = self.pvci.get_field(key)
                    self.values[codename] = value
                    LOG.debug("Measure %s, (%s, %s) value %s", codename, address, key, value)
                    self.live_socket.set_point_now(codename, value)
                    self.pullsocket.set_point_now(codename, value)
                    if self.criterium_checker.check(codename, value):
                        LOG.debug('TRIG')
                        self.database_saver.save_point_now(codename, value)
                else:
                    self.pvci.close()
                    self.live_socket.stop()
                    self.pullsocket.stop()
                    self.database_saver.stop()
                    quit = True
                    break

if __name__ == '__main__':
    """Main function """
    pvci = epimax.PVCi('/dev/serial/by-id/'
                       'usb-FTDI_USB-RS485_Cable_FT0N0UFX-if00-port0',
                       slave_address = 1)

    # Start live socket
    live_socket = LiveSocket(
        'omicron_pvci',
        list(CODENAME_TRANSLATION.keys()),
        )
    live_socket.start()

    # Start pull socket
    pullsocket = DateDataPullSocket('omicron_pvci_pull',
                                    list(CODENAME_TRANSLATION.keys()),
                                    timeouts = 2.5,
                                    )
    pullsocket.start()

    # Start database saver
    database_saver = ContinuousDataSaver(
        'dateplots_omicron', credentials.USERNAME,
        credentials.PASSWORD, list(CODENAME_TRANSLATION.keys()),
        )
    database_saver.start()

    # Criterium checker
    criterium_checker = LoggingCriteriumChecker(
        codenames=list(CODENAME_TRANSLATION.keys()),
        types=['log']*len(CODENAME_TRANSLATION.keys()),
        criteria=[0.05]*len(CODENAME_TRANSLATION.keys()),
        time_outs=[300]*len(CODENAME_TRANSLATION.keys()),
        )

    # Main loop
    data_logger = DataLogger(pvci, live_socket, pullsocket, database_saver, criterium_checker)
    data_logger.start()

    printer = ValuePrinter(data_logger)
    printer.start()

    while True:
        try:
            sleep(3)
            if not printer.is_alive():
                if data_logger.is_alive():
                    printer = ValuePrinter(data_logger)
                    printer.start()
                else:
                    print('Data logger terminated.')
                    break
        except KeyboardInterrupt:
            data_logger.stop()
            print('Data logger terminated.')
            break
