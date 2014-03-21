import time
import sys
import threading

import wiringpi2 as wp





class Watchdog(threading.Thread):
    def __init__(self):
	threading.Thread.__init__(self)
        wp.pinMode(0, 1)
	self.timer = time.time()
	self.cycle_time = 120
        self.safety_margin = 20
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

    def activate(self, pin):
        if self.watchdog.watchdog_safe:
            wp.digitalWrite(pin, 1)
        else:
            wp.digitalWrite(pin, 0)

    def deactivate(self, pin):
        wp.digitalWrite(pin, 0)

    def run(self):
        #dutycycles = [0.5,0.5,0.5,0.5,0.5,0.5]
        dutycycles = [1,1,1,1,1,1]
        #dutycycles = [0,0,0,0,0,0]
        totalcycles = 10

        self.quit = False
        cycle = 0
        while not self.quit:
            self.watchdog.reset_ttl()
            print watchdog.time_to_live
            try:
                for i in range(1,7):
                    if (1.0*cycle/totalcycles) < dutycycles[i-1]:
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

    time.sleep(1800)
    #time.sleep(240)

    watchdog.quit = True
    time.sleep(2)
    baker.quit = True
