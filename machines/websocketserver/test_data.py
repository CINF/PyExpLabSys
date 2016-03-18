from __future__ import print_function

import socket
from math import sin, pi
from time import time, sleep
from json import dumps


UDP_IP = "127.0.0.1"
UDP_PORT = 9767


sock = socket.socket(socket.AF_INET, # Internet
                     socket.SOCK_DGRAM) # UDP


while True:
    now = time()
    data = {'host': 'kenni',
            'data': {
                'sine1': [now, sin(now)],
                'sine2': [now, sin(now + pi)],
            }
    }
    print('Send:', data)
    sock.sendto(dumps(data), (UDP_IP, UDP_PORT))
    sleep(0.5)
