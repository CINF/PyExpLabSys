# -*- coding: utf-8 -*-
"""
Created on Thu Jul 17 15:39:24 2014

@author: kenni
"""

import socket
import json
import time

# REMEMBER to change the host name to the machine you are running the server
# on, 'localhost' assumes that both are being run on the same machine
HOST = 'localhost'
PORT = 8500


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_command(data):
    print
    command = 'json_wn#{}'.format(json.dumps(data))
    print 'Sending command: {}'.format(command)
    sock.sendto(command, (HOST, PORT))
    data, _ = sock.recvfrom(1024)
    if data.startswith('RET#'):
        return_value = data.split('#')[1]
        print 'Command successfull, returned: {}'.format(return_value)
    else:
        message = 'The laser did not understand the command. Return value '\
            'was: {}'.format(data)
        raise Exception(message)
    return json.loads(return_value)

### Main script
# Update settings
print send_command({'method': 'update_settings', 'power': 300, 'focus': 10})
# Change state
print send_command({'method': 'state', 'state': 'active'})
# Get the temperature measurements back from the laser as they come in
for _ in range(4):
    print send_command({'method': 'get_temperature'})
    time.sleep(2.5)

# Change state and stop
print send_command({'method': 'state', 'state': 'idle'})
time.sleep(2)  # Give it time to firing
print send_command({'method': 'stop'})
