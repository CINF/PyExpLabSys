""" Temperature controller """
from __future__ import print_function
import time
import threading
import curses
import PyExpLabSys.drivers.stahl_hv_400 as stahl_hv_400
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket


class CursesTui(threading.Thread):
    """ Text user interface for furnace heating control """
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

            for i in range(0, len(self.ioc.lenses)):
                lens = self.ioc.lenses[i]
                channel_string = "Channel " + str(i + 1) + ", " + lens + ": {0:.3f}V   "
                self.screen.addstr(5 + i, 2, channel_string.format(self.ioc.voltages[lens]))

            val = self.ioc.pushsocket.queue.qsize()
            self.screen.addstr(14, 2, "queue size: {0:.0f}s".format(val))

            val = time.time() - self.start_time
            self.screen.addstr(15, 2, "Run time: {0:.0f}s".format(val))

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
        self.pullsocket = DateDataPullSocket(name, lenses, timeouts=[3.0] * len(lenses))
        self.pullsocket.start()
        self.pushsocket = DataPushSocket(name, action='enqueue')
        self.pushsocket.start()
        self.ion_optics = stahl_hv_400.StahlHV400(port)
        self.lenses = lenses
        self.voltages = {}
        for lens in self.lenses:
            self.voltages[lens] = 0
        self.status = {}
        self.status['temperature'] = None
        self.status['output_ok'] = None
        self.quit = False

    def run(self):
        while not self.quit:
            self.status['temperature'] = self.ion_optics.read_temperature()
            self.status['output_ok'] = True # Not a permanent solution...
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                lens = str(list(element.keys())[0])
                value = element[lens]
                self.voltages[lens] = value
                channel_number = self.lenses.index(lens) + 1
                self.ion_optics.set_voltage(channel_number, value)
                qsize = self.pushsocket.queue.qsize()
            time.sleep(1)


def main():
    """ Main function """
    # The ordering of the list will set the corresponding channel number
    lenses = ['lens_a', 'lens_b', 'lens_c', 'lens_d', 'lens_e']
    port = '/dev/serial/by-id/usb-Stahl_Electronics_HV_Series_HV069-if00-port0'
    ioc = IonOpticsControl(port, 'TOF', lenses)
    ioc.start()
    time.sleep(1)

    tui = CursesTui(ioc)
    tui.daemon = True
    tui.start()

if __name__ == '__main__':
    main()
