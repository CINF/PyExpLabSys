# -*- coding: utf-8 -*-
"""Unittests for the sockets code"""

# Built-in imports
import time
import json
import SocketServer
# Allow for fast restart of a socket on a port for test purposes
SocketServer.UDPServer.allow_reuse_address = True
# Extra modules
import pytest
# Own imports
import PyExpLabSys.common.sockets
from PyExpLabSys.common.sockets import DataPullSocket, DateDataPullSocket

#from PyExpLabSys.common.utilities import get_logger
#LOGGER = get_logger('Test data socket', level='info')


# Module variables
HOST = '127.0.0.1'
NAME = 'Usage statistics from giant moon laser'

# Test fixtures
@pytest.fixture(
    params=[(DataPullSocket, False), (DataPullSocket, True), (DateDataPullSocket, False)],
    ids=['DataPullSocket', 'DataPullSocket_use_timestamp', 'DateDataPullSocket']
)
def socket_and_use_timestamp(request):
    """(Socket type, use_time_stamp) fixture"""
    return request.param


@pytest.fixture(params=[DataPullSocket, DateDataPullSocket],
                ids=['DataPullSocket', 'DateDataPullSocket'])
def sockettype(request):
    """Socket type fixture"""
    return request.param


def send_and_resc(sock, command, port):
    """Helper UPD socket send and receive"""
    sock.sendto(command, (HOST, port))
    data, _ = sock.recvfrom(1024)
    return data


# Common tests
def test_multiple_data_sockets(sockettype, sock):
    """Test general functionality with multiple sockets"""
    data_socket0 = sockettype(NAME + '1', ['meas0'], 9000)
    data_socket1 = sockettype(NAME + '2', ['meas1'], 9001)
    data_socket0.start()
    data_socket1.start()

    # Test for three points
    for n in range(3):
        now = time.time()
        data_socket0.set_point('meas0', (n, n+1))
        data_socket1.set_point('meas1', (n, now))

        # Test raw command
        data0 = send_and_resc(sock, 'raw', 9000)
        data1 = send_and_resc(sock, 'raw', 9001)
        expected0 = '{},{}'.format(n, n+1)
        expected1 = '{},{}'.format(n, now)
        assert(data0 == expected0)
        assert(data1 == expected1)

        # Test json command
        data0 = send_and_resc(sock, 'json', 9000)
        data1 = send_and_resc(sock, 'json', 9001)
        expected0 = [[n, n+1]]
        expected1 = [[n, now]]
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        # Test raw_wn command (raw with names)
        data0 = send_and_resc(sock, 'raw_wn', 9000)
        data1 = send_and_resc(sock, 'raw_wn', 9001)
        expected0 = 'meas0:{},{}'.format(n, n+1)
        expected1 = 'meas1:{},{}'.format(n, now)
        assert(data0 == expected0)
        assert(data1 == expected1)

        # Test json_wn command (json with names)
        data0 = send_and_resc(sock, 'json_wn', 9000)
        data1 = send_and_resc(sock, 'json_wn', 9001)
        expected0 = {'meas0': [n, n+1]}
        expected1 = {'meas1': [n, now]}
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        # Test codename#raw command
        data0 = send_and_resc(sock, 'meas0#raw', 9000)
        data1 = send_and_resc(sock, 'meas1#raw', 9001)
        expected0 = '{},{}'.format(n, n+1)
        expected1 = '{},{}'.format(n, now)
        assert(data0 == expected0)
        assert(data1 == expected1)

        # Test codename#json command
        data0 = send_and_resc(sock, 'meas0#json', 9000)
        data1 = send_and_resc(sock, 'meas1#json', 9001)
        expected0 = [n, n+1]
        expected1 = [n, now]
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        # Test codenames_raw command
        command = 'codenames_raw'
        data0 = send_and_resc(sock, command, 9000)
        data1 = send_and_resc(sock, command, 9001)
        expected0 = 'meas0'
        expected1 = 'meas1'
        assert(data0 == expected0)
        assert(data1 == expected1)

        # Test codenames_json command
        command = 'codenames_json'
        data0 = send_and_resc(sock, command, 9000)
        data1 = send_and_resc(sock, command, 9001)
        expected0 = ['meas0']
        expected1 = ['meas1']
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        time.sleep(0.1)  
    data_socket0.stop()
    data_socket1.stop()


def test_multiple_variables(sockettype, sock):
    """Test the general functionality with multiple measurements on a single
    socket"""
    data_socket = sockettype(NAME, ['one', 'two'])
    data_socket.start()

    # Test default port numbers
    if sockettype.__name__ == 'DateDataPullSocket':
        port = 9000
    elif sockettype.__name__ == 'DataPullSocket':
        port = 9010
    else:
        raise ValueError('Unknown class type')

    for n in range(3):
        now = time.time()
        data_socket.set_point('one', (n, n+1))
        data_socket.set_point('two', (n, now))

        # Test the raw command
        data = send_and_resc(sock, 'raw', port)
        expected = '{},{};{},{}'.format(n, n+1, n, now)
        assert(data == expected)

        # Test the json command
        data = send_and_resc(sock, 'json', port)
        expected = [[n, n+1], [n, now]]
        assert(json.loads(data) == expected)

        # Test the raw_wn command (raw with names)
        data = send_and_resc(sock, 'raw_wn', port)
        expected = 'one:{},{};two:{},{}'.format(n, n+1, n, now)
        assert(expected == data)

        # Test the json_wn command (json with names)
        data = send_and_resc(sock, 'json_wn', port)
        expected = {'one': [n, n+1], 'two': [n, now]}
        assert(expected == json.loads(data))

        # Test the codename#raw command
        data0 = send_and_resc(sock, 'one#raw', port)
        data1 = send_and_resc(sock, 'two#raw', port)
        expected0 = '{},{}'.format(n, n+1)
        expected1 = '{},{}'.format(n, now)
        assert(data0 == expected0)
        assert(data1 == expected1)

        # Test the codename#json command
        data0 = send_and_resc(sock, 'one#json', port)
        data1 = send_and_resc(sock, 'two#json', port)
        expected0 = [n, n+1]
        expected1 = [n, now]
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        # Test the codenames_raw command
        data = send_and_resc(sock, 'codenames_raw', port)
        expected = 'one,two'
        assert(data == expected)

        # Test the codenames_json command
        data = send_and_resc(sock, 'codenames_json', port)
        expected = ['one', 'two']
        assert(json.loads(data) == expected)

        time.sleep(0.1)
    data_socket.stop()


def test_define_timeout(sockettype):
    """Test the definition of the timeouts and the cleaning up of data with
    stop"""
    # Test one measurement with single timeout
    data_socket = sockettype(NAME, ['one'], port=7000, timeouts=47)
    data_socket.start()
    assert(PyExpLabSys.common.sockets.DATA[7000]['timeouts'] == {'one': 47})
    data_socket.stop()
    assert(PyExpLabSys.common.sockets.DATA.get(7000) is None)
    del data_socket

    # Test one measurement with single timeout in list
    data_socket = sockettype(NAME, ['one'], port=7000, timeouts=[47])
    data_socket.start()
    assert(PyExpLabSys.common.sockets.DATA[7000]['timeouts'] == {'one': 47})
    data_socket.stop()
    assert(PyExpLabSys.common.sockets.DATA.get(7000) is None)
    del data_socket

    # Test two measurements with single timeout
    data_socket = sockettype(NAME, ['one', 'two'], port=7000, timeouts=42)
    data_socket.start()
    expected = {'one': 42, 'two': 42}
    assert(PyExpLabSys.common.sockets.DATA[7000]['timeouts'] == expected)
    data_socket.stop()
    assert(PyExpLabSys.common.sockets.DATA.get(7000) is None)
    del data_socket

    # Test two measurements with two timeouts in list
    data_socket = sockettype(NAME, ['one', 'two'], port=7000,
                             timeouts=[42, 47])
    data_socket.start()
    expected = {'one': 42, 'two': 47}
    assert(PyExpLabSys.common.sockets.DATA[7000]['timeouts'] == expected)
    data_socket.stop()
    assert(PyExpLabSys.common.sockets.DATA.get(7000) is None)
    del data_socket


def test_data_timeout(socket_and_use_timestamp, sock):
    sockettype, usetimestamp = socket_and_use_timestamp
    data_socket = sockettype(NAME, ['one', 'two'], timeouts=[0.1, 10],
                             port=9000)
    data_socket.start()

    now = time.time()
    if sockettype.__name__ == 'DateDataPullSocket':
        x1 = now
        x2 = now
        y1 = 42.0
        y2 = 47.0
    elif sockettype.__name__ == 'DataPullSocket':
        x1 = 9.7
        x2 = 15.3
        y1 = 100
        y2 = 111
    else:
        raise ValueError('Unknown class type')

    if usetimestamp:
        data_socket.set_point('one', (x1, y1), timestamp=now)
        data_socket.set_point('two', (x2, y2), timestamp=now)

    else:
        data_socket.set_point('one', (x1, y1))
        data_socket.set_point('two', (x2, y2))
    
    time.sleep(0.15)  # Obsoletes the first point

    data = send_and_resc(sock, 'raw', 9000)
    expected = '{};{},{}'.format('OLD_DATA', x2, y2)
    assert(data == expected)

    data = send_and_resc(sock, 'json', 9000)
    expected = ['OLD_DATA', [x2, y2]]
    assert(json.loads(data) == expected)

    data = send_and_resc(sock, 'raw_wn', 9000)
    expected = 'one:OLD_DATA;two:{},{}'.format(x2, y2)
    assert(expected == data)

    data = send_and_resc(sock, 'json_wn', 9000)
    expected = {'one': 'OLD_DATA', 'two': [x2, y2]}
    assert(expected == json.loads(data))

    data0 = send_and_resc(sock, 'one#raw', 9000)
    data1 = send_and_resc(sock, 'two#raw', 9000)
    expected0 = 'OLD_DATA'
    expected1 = '{},{}'.format(x2, y2)
    assert(data0 == expected0)
    assert(data1 == expected1)

    data0 = send_and_resc(sock, 'one#json', 9000)
    data1 = send_and_resc(sock, 'two#json', 9000)
    expected0 = 'OLD_DATA'
    expected1 = [x2, y2]
    assert(json.loads(data0) == expected0)
    assert(json.loads(data1) == expected1)

    data_socket.stop()
