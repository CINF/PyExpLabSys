""" Ion Optics Control software """
from __future__ import print_function
import time
import threading
import curses
import PyExpLabSys.drivers.stahl_hv_400 as stahl_hv_400
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class CursesTui(threading.Thread):
    """ Text user interface for ion optics control """
    def __init__(self, ioc_class):
        threading.Thread.__init__(self)
        self.start_time = time.time()
        self.quit = False
        self.ioc = ioc_class
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)

    def run(self):
        while not self.quit:
            self.screen.addstr(2, 2, 'Running')
            val = self.ioc.status['temperature']
            self.screen.addstr(3, 2, "Device Temeperature: {0:.2f}C  ".format(val))
            if self.ioc.status['output_error'] is False:
                self.screen.addstr(4, 2, "All channels ok ")
            else:
                self.screen.addstr(4, 2, "Error in channel")

            self.screen.addstr(7, 13, 'Set voltage')
            self.screen.addstr(7, 27, 'Measured')
            self.screen.addstr(7, 38, 'Status')
            for i in range(0, len(self.ioc.lenses)):
                lens = self.ioc.lenses[i]
                ch_string = "Channel " + str(i + 1) + ":  {0: >9.2f}V   {1: >7.1f}V     {2}  "
                set_v = self.ioc.set_voltages[lens]
                actual_v = self.ioc.actual_voltages[lens]
                status = self.ioc.status['channel_status'][i+1]
                self.screen.addstr(8 + i, 2, ch_string.format(set_v, actual_v, status))

            val = self.ioc.pushsocket.queue.qsize()
            self.screen.addstr(16, 2, "queue size: {0:.0f}".format(val))

            val = time.time() - self.start_time
            self.screen.addstr(17, 2, "Run time: {0:.0f}s".format(val))

            key_pressed = self.screen.getch()
            if key_pressed == ord('q'):
                self.ioc.quit = True
                self.quit = True

            self.screen.refresh()
            time.sleep(0.2)
        self.stop()

    def stop(self):
        """ Clean up console """
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()


class IonOpticsControl(threading.Thread):
    """ Main optics control """
    def __init__(self, port, name, lenses):
        threading.Thread.__init__(self)
        name = name + '_ion_optics'
        self.pullsocket = DateDataPullSocket(name, lenses, timeouts=20.0)
        self.pullsocket.start()
        self.pushsocket = DataPushSocket(name, action='enqueue')
        self.pushsocket.start()
        self.ion_optics = stahl_hv_400.StahlHV400(port)
        self.lenses = lenses
        self.set_voltages = {}
        self.actual_voltages = {}
        for lens in self.lenses:
            self.set_voltages[lens] = 0
            self.actual_voltages[lens] = 0
        self.status = {}
        self.status['channel_status'] = {}
        for i in range(1, len(self.lenses)+1):
            self.status['channel_status'][i] = False
        self.status['temperature'] = None
        self.status['output_error'] = None
        self.quit = False

    def run(self):
        current_lens = 1
        while not self.quit:
            self.status['temperature'] = self.ion_optics.read_temperature()
            if self.status['temperature'] > 50:
                for lens in self.lenses:
                    self.set_voltages[lens] = 0

            self.status['channel_status'] = self.ion_optics.check_channel_status()
            self.status['output_error'] = False in self.status['channel_status']

            actual_voltage = self.ion_optics.query_voltage(current_lens)
            self.actual_voltages[self.lenses[current_lens-1]] = actual_voltage
            self.pullsocket.set_point_now(self.lenses[current_lens-1], actual_voltage)

            if current_lens == len(self.lenses):
                current_lens = 1
            else:
                current_lens += 1

            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                lens = str(list(element.keys())[0])
                value = element[lens]
                self.set_voltages[lens] = value
                channel_number = self.lenses.index(lens) + 1
                self.ion_optics.set_voltage(channel_number, value)
                qsize = self.pushsocket.queue.qsize()
            time.sleep(0.1)
