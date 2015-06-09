""" App to control PW-modulated bakeout boxes """
# -*- coding: utf-8 -*-
import time
import sys
import threading
import curses
import wiringpi2 as wp # pylint: disable=F0401
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.utilities import get_logger

sys.path.append('/home/pi/PyExpLabSys/machines/' + sys.argv[1])
import settings # pylint: disable=F0401

LOGGER = get_logger('Bakeout', level='warn', file_log=True,
                    file_name='bakeout_log.txt', terminal_log=False)

class CursesTui(threading.Thread):
    """ Text UI for bakeout program """
    def __init__(self, baker_instance):
        threading.Thread.__init__(self)
        self.baker = baker_instance
        self.watchdog = baker_instance.watchdog
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)

    def run(self):
        while not self.baker.quit:
            self.screen.addstr(2, 2, 'Running')

            tui_string = "Watchdog TTL: {0:.0f}   "
            self.screen.addstr(4, 2, tui_string.format(self.watchdog.time_to_live))
            tui_string = "Watchdog Timer: {0:.1f}"
            self.screen.addstr(5, 2, tui_string.format(time.time() - self.watchdog.timer))
            self.screen.addstr(6, 2, "Watchdog safe: " + 
                               str(self.watchdog.watchdog_safe) + ' ') 

            self.screen.addstr(8, 2, 'Current channel status:')
            for i in range(1, 7):
                self.screen.addstr(9, 6 * i, str(wp.digitalRead(i)))

            self.screen.addstr(12, 2, 'Channel duty cycles')
            for i in range(1, 7):
                self.screen.addstr(13, 7 * i, str(self.baker.dutycycles[i - 1]) + '    ')

            key = self.screen.getch()

            self.screen.addstr(20, 2, str(key) + '     ')

            if key == ord('1'):
                self.baker.modify_dutycycle(1, 0.01)
            if key == ord('!'):
                self.baker.modify_dutycycle(1, -0.01)
            if key == ord('2'):
                self.baker.modify_dutycycle(2, 0.01)
            if key == ord('"'):
                self.baker.modify_dutycycle(2, -0.01)
            if key == ord('3'):
                self.baker.modify_dutycycle(3, 0.01)
            if key == ord('#'):
                self.baker.modify_dutycycle(3, -0.01)
            if key == ord('4'):
                self.baker.modify_dutycycle(4, 0.01)
            if key == 194: #... '¤':
                self.baker.modify_dutycycle(4, -0.01)
            if key == ord('5'):
                self.baker.modify_dutycycle(5, 0.01)
            if key == ord('%'):
                self.baker.modify_dutycycle(5, -0.01)
            if key == ord('6'):
                self.baker.modify_dutycycle(6, 0.01)
            if key == ord('&'):
                self.baker.modify_dutycycle(6, -0.01)
            if key == ord('q'):
                self.baker.quit = True
                self.screen.addstr(2, 2, 'Quitting....')

            self.screen.refresh()
            time.sleep(0.2)

    def stop(self):
        """ Leave the terminal in a clean state """
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()    



class Watchdog(threading.Thread):
    """ Make sure heating stops if control loop fails """
    def __init__(self):
        threading.Thread.__init__(self)
        wp.pinMode(0, 1)
        self.timer = time.time()
        self.cycle_time = settings.cycle_time
        self.safety_margin = settings.safety_margin
        self.watchdog_safe = True
        self.quit = False
        self.time_to_live = 0
        self.reactivate()#Initially activate Watchdog
        self.reset_ttl()

    def reset_ttl(self):
        """ Reset ttl """
        self.time_to_live = 100

    def decrease_ttl(self):
        """ Decrease ttl """
        self.time_to_live = self.time_to_live - 1

    def reactivate(self):
        """ Reactivate safety timer """
        wp.digitalWrite(0, 1)
        time.sleep(0.1)
        wp.digitalWrite(0, 0)
        return None

    def run(self):
        while not self.quit:
            self.decrease_ttl()
            if self.time_to_live < 0:
                self.quit = True
            delta_t = time.time() - self.timer
            allowed_time = self.cycle_time - self.safety_margin
            reactivate_time = self.cycle_time + self.safety_margin
            if delta_t < allowed_time:
                self.watchdog_safe = True
            else:
                self.watchdog_safe = False
            if delta_t > reactivate_time:
                self.reactivate()
                self.timer = time.time()
            time.sleep(0.2)
        self.watchdog_safe = False


class Bakeout(threading.Thread):
    """ The actual heater """
    def __init__(self):
        threading.Thread.__init__(self)
        self.watchdog = Watchdog()
        self.watchdog.daemon = True
        self.watchdog.start()
        time.sleep(1)

        self.setup = settings.setup
        self.quit = False
        for i in range(0, 7): #Set GPIO pins to output
            wp.pinMode(i, 1)
        self.setup = settings.setup
        self.dutycycles = [0, 0, 0, 0, 0, 0]
        self.livesocket = LiveSocket(self.setup + '-bakeout',
                                     ['1', '2', '3', '4', '5', '6'], 1)
        self.livesocket.start()
        self.pushsocket = DataPushSocket(self.setup + '-push_control', action='enqueue')
        self.pushsocket.start()

    def activate(self, pin):
        """ Activate a pin """
        if settings.count_from_right:
            pin = pin
        else:
            pin = 7 - pin
        if self.watchdog.watchdog_safe:
            wp.digitalWrite(pin, 1)
        else:
            wp.digitalWrite(pin, 0)

    def deactivate(self, pin):
        """ De-activate a pin """
        if settings.count_from_right:
            pin = pin
        else:
            pin = 7 - pin
        wp.digitalWrite(pin, 0)

    def modify_dutycycle(self, channel, amount=None, value=None):
        """ Change the dutycycle of a channel """
        if amount is not None:
            self.dutycycles[channel-1] =  self.dutycycles[channel-1] + amount
        if value is not None:
            self.dutycycles[channel-1] = value

        if  self.dutycycles[channel-1] > 1:
            self.dutycycles[channel-1] = 1
        if self.dutycycles[channel-1] < 0.0001:
            self.dutycycles[channel-1] = 0
        self.livesocket.set_point_now(str(channel), self.dutycycles[channel-1])
        return self.dutycycles[channel-1]

    def run(self):
        totalcycles = settings.number_of_cycles

        self.quit = False
        cycle = 0
        while not self.quit:
            start_time = time.time()
            qsize = self.pushsocket.queue.qsize()
            LOGGER.debug('qsize: ' + str(qsize))
            while qsize > 0:
                element = self.pushsocket.queue.get()
                LOGGER.debug('Element: ' + str(element))
                channel = element.keys()[0]
                value = element[channel]
                self.modify_dutycycle(int(channel), value=value) 
                qsize = self.pushsocket.queue.qsize()

            self.watchdog.reset_ttl()
            for i in range(1, 7):
                if (1.0*cycle/totalcycles) < self.dutycycles[i-1]:
                    self.activate(i)
                else:
                    self.deactivate(i)
            cycle = cycle + 1
            cycle = cycle % totalcycles
            run_time = time.time() - start_time
            sleep_time = 1.0 * settings.cycle_time / settings.number_of_cycles
            try:
                time.sleep(sleep_time - run_time)
            except IOError:
                self.quit = True
                LOGGER.fatal('Program runs too slow to perform this operation!')
        for i in range(0, 7): # Ready to quit
            self.deactivate(i)



if __name__ == '__main__':
    wp.wiringPiSetup()

    time.sleep(1)
    BAKER = Bakeout()
    BAKER.start()

    TUI = CursesTui(BAKER)
    TUI.start()

    while not BAKER.quit:
        time.sleep(1)

