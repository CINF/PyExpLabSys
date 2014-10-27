# pylint: disable=C0301,R0904, C0103

"""
Self contained module to run a SPECS sputter gun including fall-back text gui
"""

import serial
import time
import threading
import curses
import socket
import json

from PyExpLabSys.drivers.specs_XRC1000 import XRC1000

EXCEPTION = None
log = open('error_log.txt', 'w')


class CursesTui(threading.Thread):
    """ Defines a fallback text-gui for the source control. """
    def __init__(self, sourcecontrol):
        threading.Thread.__init__(self)
        self.sc = sourcecontrol
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(False)
        self.screen.keypad(1)
        self.screen.nodelay(1)
        self.time = time.time()
        self.countdown = False
        self.last_key = None
        self.running = True

    def run(self):
        while self.running:
            self.screen.addstr(3, 2, 'X-ray Source Control, ID:  ' + str(self.sc.status['ID']))

            if self.sc.status['degas']:
                self.screen.addstr(4, 2, "Degassing")

            if self.sc.status['remote']:
                self.screen.addstr(5, 2, "Control mode: Remote")
            else:
                self.screen.addstr(5, 2, "Control mode: Local")

            if self.sc.status['standby']:
                self.screen.addstr(6, 2, "Device status, Standby: ON  ")
            else:
                self.screen.addstr(6, 2, "Device status, Standby: OFF  ")
                
            if self.sc.status['hv']:
                self.screen.addstr(7, 2, "Device status: HV ON  ")
            else:
                self.screen.addstr(7, 2, "Device status: HV OFF  ")

            if self.sc.status['operate']:
                self.screen.addstr(8, 2, "Device status: Operate ON ")
            else:
                self.screen.addstr(8, 2, "Device status, Operate: OFF ")
            
            #if self.sc.status['error'] != None:
            #    self.screen.addstr(9, 2, "Error: " + str(self.sc.status['error']))

            try:
                self.screen.addstr(10, 2, "Filament bias: {0:.3f}V          ".format(self.sc.status['filament_bias']))
                self.screen.addstr(11, 2, "Filament Current: {0:.2f}A          ".format(self.sc.status['filament_current']))
                self.screen.addstr(12, 2, "Filament Power: {0:.2f}W          ".format(self.sc.status['filament_power']))
                self.screen.addstr(13, 2, "Emission Current: {0:.4f}A          ".format(self.sc.status['emission_current']))
                self.screen.addstr(14, 2, "Anode Voltage: {0:.2f}V          ".format(self.sc.status['anode_voltage']))
                self.screen.addstr(15, 2, "Anode Power: {0:.2f}W          ".format(self.sc.status['anode_power']))
                self.screen.addstr(16, 2, "Water flow: {0:.2f}L/min       ".format(self.sc.status['water_flow']))
            except Exception as exception:
                global EXCEPTION
                EXCEPTION = exception
                #self.screen.addstr(10,2, exception.message)
                self.screen.addstr(10, 2, "Filament bias: -                   ")
                self.screen.addstr(11, 2, "Filament Current: -                           ")
                self.screen.addstr(12, 2, "Filament Power: -                           ")
                self.screen.addstr(13, 2, "Emission Current: -                             ")
                self.screen.addstr(14, 2, "Anode Voltage: -                          ")
                self.screen.addstr(15, 2, "Anode Power: -                      ")
                self.screen.addstr(16, 2, "water flow: -                          ")
            if self.sc.status['error'] != None:
                self.screen.addstr(18, 2, "Latest error message: " + str(self.sc.status['error']) + " at time: " + str(self.sc.status['error time']))

            self.screen.addstr(19, 2, "Runtime: {0:.0f}s       ".format(time.time() - self.time))
            if self.countdown:
                self.screen.addstr(18, 2, "Time until shutdown: {0:.0f}s       ".format(self.countdown_end_time -time.time()))
                if time.time() > self.countdown_end_time:
                    self.sc.goto_off = True
                    self.countdown = False
            
            self.screen.addstr(21, 2, 'q: quit program, s: standby, o: operate, c: cooling, x: shutdown gun')
            self.screen.addstr(22, 2, ' 3: shutdown in 3h, r: change to remote')
            
            self.screen.addstr(24, 2, ' Latest key: ' + str(self.last_key))

            n = self.screen.getch()
            if n == ord('q'):
                self.sc.running = False
                self.running = False
                self.last_key = chr(n)
            elif n == ord('s'):
                self.sc.goto_standby = True
                self.last_key = chr(n)
            elif n == ord('o'):
                self.sc.goto_operate = True
                self.last_key = chr(n)
            elif n == ord('c'):
                self.sc.goto_cooling = True
                self.last_key = chr(n)
            elif n == ord('x'):
                self.sc.goto_off = True
                self.last_key = chr(n)
            elif n == ord('r'):
                self.sc.goto_remote = True
                self.last_key = chr(n)
            elif n == ord('3'):
                self.countdown = True
                self.countdown_end_time = float(time.time() + 3*3600.0) # second
                self.last_key = chr(n)
            
            # disable s o key
            #if n == ord('s'):
            #    self.sc.goto_standby = True
            #if n == ord('o'):
            #    self.sc.goto_operate = True

            self.screen.refresh()
            time.sleep(1)
        time.sleep(5)
        self.stop()
        print EXCEPTION

    def stop(self):
        """ Cleanup the terminal """
        try:
            self.sc.stop()
        except:
            pass
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()


if __name__ == '__main__':
    print('Program start')
    sc = XRC1000()
    sc.daemon = True
    sc.start()

    tui = CursesTui(sc)
    #tui.daemon = True
    tui.start()
