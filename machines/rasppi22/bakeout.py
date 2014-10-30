# -*- coding: utf-8 -*-
import time
import sys
import threading
import curses
import wiringpi2 as wp

#6: Ion pumps
#5: Diverse rør
#4: Main chamber + turbo
#2: Flight tube

class CursesTui(threading.Thread):
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

            self.screen.addstr(4, 2, "Watchdog TTL: {0:.0f}  ".format(self.watchdog.time_to_live))
            self.screen.addstr(5, 2, "Watchdog Timer: {0:.1f}".format(time.time() - self.watchdog.timer))
            self.screen.addstr(6, 2, "Watchdog safe: " + str(self.watchdog.watchdog_safe)) 

            self.screen.addstr(8,2, 'Current channel status:')
            for i in range(1,7):
                self.screen.addstr(9,6*i, str(wp.digitalRead(i)))

            self.screen.addstr(12,2, 'Channel duty cycles')
            for i in range(1,7):
                self.screen.addstr(13,6*i, str(self.baker.dutycycles[i-1]))

            n = self.screen.getch()

            self.screen.addstr(20,2, str(n) + '     ')

            if n == ord('1'):
                self.baker.modify_dutycycle(1,0.1)
            if n == ord('!'):
                self.baker.modify_dutycycle(1,-0.1)
            if n == ord('2'):
                self.baker.modify_dutycycle(2,0.1)
            if n == ord('"'):
                self.baker.modify_dutycycle(2,-0.1)
            if n == ord('3'):
                self.baker.modify_dutycycle(3,0.1)
            if n == ord('#'):
                self.baker.modify_dutycycle(3,-0.1)
            if n == ord('4'):
                self.baker.modify_dutycycle(4,0.1)
            if n == 194: #... '¤':
                self.baker.modify_dutycycle(4,-0.1)
            if n == ord('5'):
                self.baker.modify_dutycycle(5,0.1)
            if n == ord('%'):
                self.baker.modify_dutycycle(5,-0.1)
            if n == ord('6'):
                self.baker.modify_dutycycle(6,0.1)
            if n == ord('&'):
                self.baker.modify_dutycycle(6,-0.1)

            if n == ord('q'):
                self.baker.quit = True
                self.screen.addstr(2, 2, 'Quitting....')

            self.screen.refresh()
            time.sleep(0.2)

    def stop(self):
        curses.nocbreak()
        self.screen.keypad(0)
        curses.echo()
        curses.endwin()    



class Watchdog(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
        wp.pinMode(0, 1)
	self.timer = time.time()
	self.cycle_time = 120
        self.safety_margin = 3
        self.watchdog_safe = True
        self.quit = False
        self.time_to_live = 0
        self.reactivate()#Watchdog is initially activated
        self.reset_ttl()

    def reset_ttl(self):
        self.time_to_live = 100

    def decrease_ttl(self):
        self.time_to_live = self.time_to_live - 1

    def reactivate(self):
        wp.digitalWrite(0, 1)
        time.sleep(0.1)
        wp.digitalWrite(0, 0)
        return None

    def run(self):
        while not self.quit:
            self.decrease_ttl()
            if self.time_to_live < 0:
                self.quit = True
            dt = time.time() - self.timer
            allowed_time = self.cycle_time - self.safety_margin
            reactivate_time = self.cycle_time + self.safety_margin
            if dt < allowed_time:
                self.watchdog_safe = True
            else:
                self.watchdog_safe = False
            if dt > reactivate_time:
                self.reactivate()
                self.timer = time.time()
            time.sleep(0.2)
        self.watchdog_safe = False


class Bakeout(threading.Thread):
    def __init__(self, watchdog):
	threading.Thread.__init__(self)
        self.watchdog = watchdog
        self.quit = False
        for i in range(0, 7): #Set GPIO pins to output
            wp.pinMode(i, 1)
        self.dutycycles = [0.0,0.0,0.0,0.0,0.0,0.0]
        self.run_ramp = False

    def activate(self, pin):
        if self.watchdog.watchdog_safe:
            wp.digitalWrite(pin, 1)
        else:
            wp.digitalWrite(pin, 0)

    def deactivate(self, pin):
        wp.digitalWrite(pin, 0)

    def modify_dutycycle(self, channel, amount):
        self.dutycycles[channel-1] =  self.dutycycles[channel-1] + amount
        if  self.dutycycles[channel-1] > 1:
             self.dutycycles[channel-1] = 1.0
        if self.dutycycles[channel-1] < 0.01:
             self.dutycycles[channel-1] = 0.0
        return  self.dutycycles[channel-1]

    def set_dutycycle(self, channel, value):
        self.dutycycles[channel-1] =  value
        if  self.dutycycles[channel-1] > 1:
             self.dutycycles[channel-1] = 1.0
        if self.dutycycles[channel-1] < 0.01:
             self.dutycycles[channel-1] = 0.0
        return  self.dutycycles[channel-1]


    def set_all_dutycycle(self,value_list):
        if len(value_list) == 7: #first value is always 0
            for value,index in value_list.itemize():
                self.set_dutycycle(index, value)
        return self.dutycycle

    def load_ramp(self,):
        import ramp
        reload(ramp)
        self.ramp = ramp.ramp()
        self.run_ramp = True
        
    def run(self):
        totalcycles = 10

        self.quit = False
        cycle = 0
        while not self.quit:
            self.watchdog.reset_ttl()
            if self.run_ramp == True:
                self.set_all_dutycycle(self.ramp.present())
            try:
                for i in range(1,7):
                    if (1.0*cycle/totalcycles) < self.dutycycles[i-1]:
                        baker.activate(i)
                    else:
                        baker.deactivate(i)
                cycle = cycle + 1
                cycle = cycle % totalcycles
                time.sleep(1)
            except:
                self.quit = True
                print "Program terminated by user"
                print sys.exc_info()[0]
                print sys.exc_info()[1]
                print sys.exc_info()[2]
                for i in range(0, 7):
                    baker.deactivate(i)



if __name__ == '__main__':
    wp.wiringPiSetup()

    watchdog = Watchdog()
    watchdog.daemon = True
    watchdog.start()
    time.sleep(1)
    baker = Bakeout(watchdog)
    baker.start()

    tui = CursesTui(baker)
    #tui.daemon = True
    tui.start()

    while not baker.quit:
        time.sleep(1)

    watchdog.quit = True
    time.sleep(2)
    baker.quit = True
