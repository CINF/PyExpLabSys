"""
This module implements the necessary interface to control
a valve box using standard gpio commands
"""
from __future__ import print_function
import time
import threading
import wiringpi as wp
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

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
            time.sleep(0.1)
            qsize = self.pushsocket.queue.qsize()
            print(qsize)
            while qsize > 0:
                element = self.pushsocket.queue.get()
                valve = list(element.keys())[0]
                wp.digitalWrite(int(valve)-1, element[valve])
                qsize = self.pushsocket.queue.qsize()

            for j in range(0, 20):
                self.pullsocket.set_point_now(self.valves[j], wp.digitalRead(j))
