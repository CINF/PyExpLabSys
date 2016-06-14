from __future__ import print_function

import sys
sys.path.insert(1, '/home/pi/tmp/PyExpLabSys')

from PyExpLabSys.common.sockets import LiveSocket

import socket
from math import sin, pi, cos
from time import time, sleep
from json import dumps


ls = LiveSocket('test socket on 71', ['sine1', 'sine2', 'status', 'cosine1', 'cosine2'], internal_data_pull_socket_port=7999)


start = time()

count = 0
while True:
    count += 1
    now = time()

    # Set sines
    data = {
        'sine1': sin(now),
        'sine2': sin(now + pi),
    }
    ls.set_batch_now(data)

    # Set cosines
    if time() - start > 6.28:
        start = time()
        ls.reset(['cosine1', 'cosine2'])
    x = time() - start
    data = {
        'cosine1': [x, cos(x)],
        'cosine2': [x, cos(x + pi)],
    }
    ls.set_batch(data)


    if count % 2 == 0:
        ls.set_point_now('status', 'OK')
    else:
        ls.set_point_now('status', 'even better')
    #if count % 10 == 0:
    #    print(sock.recv(1024))
    sleep(0.1)
