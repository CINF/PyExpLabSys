# -*- coding: utf-8 -*-
"""Power supply server tester"""

import socket
import json

HOST, PORT = "localhost", 8500
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

class PowerSupplyComException(Exception):
    pass


def send_command(output, command, arg=None):
    data_to_send = {'command': command, 'output': output}
    if arg is not None:
        data_to_send['arg'] = arg
    formatted_command = b'json_wn#' + json.dumps(data_to_send).encode('utf-8')

    sock.sendto(formatted_command, (HOST, PORT))
    received = sock.recv(1024).decode('utf-8')

    if received.startswith('ERROR:'):
        raise PowerSupplyComException(received)

    # The return values starts with RET#
    return json.loads(received[4:])


print("SCL", send_command('1', 'set_current_limit', 0.7))
print("RCL", send_command('1', 'read_current_limit'))
print("SOS", send_command('1', 'output_status', True))
print("SV", send_command('1', 'set_voltage', 0.2))
print("RSV", send_command('1', 'read_set_voltage'))
print("RAV", send_command('1', 'read_actual_voltage'))
print("RAC", send_command('1', 'read_actual_current'))
print(send_command('1', 'output_status', False))