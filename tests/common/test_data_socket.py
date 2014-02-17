# -*- coding: utf-8 -*-
"""Unittests for the sockets code"""

# Built-in imports
import time
import socket
import json
# Own imports
from PyExpLabSys.common.sockets import DataSocket


def test_multiple_data_sockets():
    """Test interaction with multiple data sockets"""
    data_socket0 = DataSocket(['meas0'], 9000)
    data_socket1 = DataSocket( ['meas1'], 9001)
    data_socket0.start()
    data_socket1.start()
    
    HOST = "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    for n in range(3):
        now = time.time()
        data_socket0.set_point('meas0', (n, n+1))
        data_socket1.set_point('meas1', (n, now))

        command = 'raw'
        sock.sendto(command, (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto(command, (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = '{},{}'.format(n, n+1)
        expected1 = '{},{}'.format(n, now)
        assert(data0 == expected0)
        assert(data1 == expected1)

        command = 'json'
        sock.sendto(command, (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto(command, (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = [[n, n+1]]
        expected1 = [[n, now]]
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        command = 'raw_wn'
        sock.sendto(command, (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto(command, (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = 'meas0:{},{}'.format(n, n+1)
        expected1 = 'meas1:{},{}'.format(n, now)
        assert(data0 == expected0)
        assert(data1 == expected1)

        command = 'json_wn'
        sock.sendto(command, (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto(command, (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = {'meas0': [n, n+1]}
        expected1 = {'meas1': [n, now]}
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        sock.sendto('meas0#raw', (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto('meas1#raw', (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = '{},{}'.format(n, n+1)
        expected1 = '{},{}'.format(n, now)
        assert(data0 == expected0)
        assert(data1 == expected1)

        sock.sendto('meas0#json', (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto('meas1#json', (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = [n, n+1]
        expected1 = [n, now]
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        command = 'codenames_raw'
        sock.sendto(command, (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto(command, (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = 'meas0'
        expected1 = 'meas1'
        assert(data0 == expected0)
        assert(data1 == expected1)

        command = 'codenames_json'
        sock.sendto(command, (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto(command, (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = ['meas0']
        expected1 = ['meas1']
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        time.sleep(0.1)
    
    data_socket0.stop()
    data_socket1.stop()
    time.sleep(0.1)

    print 'multiple sockets done'


def test_multiple_variables():
    """Test interaction with a single data socket with multiple variables"""
    data_socket = DataSocket(['one', 'two'])  # Test default port 9000
    data_socket.start()

    HOST = "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for n in range(3):
        now = time.time()
        data_socket.set_point('one', (n, n+1))
        data_socket.set_point('two', (n, now))

        sock.sendto('raw', (HOST, 9000))
        data, _ = sock.recvfrom(1024)
        expected = '{},{};{},{}'.format(n, n+1, n, now)
        assert(data == expected)

        sock.sendto('json', (HOST, 9000))
        data, _ = sock.recvfrom(1024)
        expected = [[n, n+1], [n, now]]
        assert(json.loads(data) == expected)

        sock.sendto('raw_wn', (HOST, 9000))
        data, _ = sock.recvfrom(1024)
        expected = 'one:{},{};two:{},{}'.format(n, n+1, n, now)
        assert(expected == data)

        sock.sendto('json_wn', (HOST, 9000))
        data, _ = sock.recvfrom(1024)
        expected = {'one': [n, n+1], 'two': [n, now]}
        assert(expected == json.loads(data))

        sock.sendto('one#raw', (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto('two#raw', (HOST, 9000))
        data1, _ = sock.recvfrom(1024)
        expected0 = '{},{}'.format(n, n+1)
        expected1 = '{},{}'.format(n, now)
        assert(data0 == expected0)
        assert(data1 == expected1)

        sock.sendto('one#json', (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto('two#json', (HOST, 9000))
        data1, _ = sock.recvfrom(1024)
        expected0 = [n, n+1]
        expected1 = [n, now]
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        command = 'codenames_raw'
        sock.sendto(command, (HOST, 9000))
        data, _ = sock.recvfrom(1024)
        expected = 'one,two'
        assert(data == expected)

        command = 'codenames_json'
        sock.sendto(command, (HOST, 9000))
        data, _ = sock.recvfrom(1024)
        expected = ['one', 'two']
        assert(json.loads(data) == expected)

        time.sleep(0.1)

    data_socket.stop()
    time.sleep(0)

    print 'multiple variables done'

test_multiple_data_sockets()
test_multiple_variables()
print 'Done'
