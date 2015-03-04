# pylint: disable=R0913,W0142,C0103 

"""
This module implements the necessary interface to control
a valve box using standard gpio commands
"""

import time
import threading
import wiringpi2 as wp

class ValveControl(threading.Thread):
    """ Keeps status of all valves """
    def __init__(self, valves, pullsocket, pushsocket):
        threading.Thread.__init__(self)
        wp.wiringPiSetup()
        time.sleep(1)
        for index in range(0, 21):  # Set GPIO pins to output
            wp.pinMode(index, 1)
            wp.digitalWrite(index, 0)
        # Now that all output are low, we can open main safety output
        wp.digitalWrite(20, 1)

        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.running = True
        self.valves = valves

    def run(self):
        while self.running:
            time.sleep(0.5)
            qsize = self.pushsocket.queue.qsize()
            print qsize
            while qsize > 0:
                element = self.pushsocket.queue.get()
                valve = element.keys()[0]
                wp.digitalWrite(int(valve)-1, element[valve])
                qsize = self.pushsocket.queue.qsize()

            for j in range(0, 20):
                self.pullsocket.set_point_now(self.valves[j], wp.digitalRead(j))
