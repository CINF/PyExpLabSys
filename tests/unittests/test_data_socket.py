# -*- coding: utf-8 -*-
"""Unittests for the sockets code"""

# Built-in imports
import time
import socket
import json
import SocketServer
# Allow for fast restart of a socket on a port for test purposes
SocketServer.UDPServer.allow_reuse_address = True
# Extra modules
import pytest
# Own imports
import PyExpLabSys.common.sockets
from PyExpLabSys.common.sockets import DataSocket, DateDataSocket, LiveSocket

### DataSocket tests
def test_data_multiple_data_sockets():
    multiple_data_sockets(DataSocket)

def test_data_multiple_variables():
    multiple_variables(DataSocket)

def test_data_define_timeout():
    define_timeout(DataSocket)

def test_data_timeout():
    data_timeout(DataSocket)

def test_data_timeout_with_timestamp():
    data_timeout(DataSocket, usetimestamp=True)

### DateSataSocket tests
def test_date_multiple_data_sockets():
    multiple_data_sockets(DateDataSocket)

def test_date_multiple_variables():
    multiple_variables(DateDataSocket)

def test_date_define_timeout():
    define_timeout(DateDataSocket)

def test_date_data_timeout():
    data_timeout(DateDataSocket)

### LiveSocket test
def test_live_init():
    codenames = ['name1', 'name2']
    live_socket = LiveSocket(codenames, 1.0)
    live_socket.start()

    # Check that the port default is 8000
    assert(live_socket.port == 8000)

    data = PyExpLabSys.common.sockets.DATA
    # Check that data and last served are initialized and not with the same
    # objects
    for codename in codenames:
        assert(data[8000]['data'][codename] ==
               data[8000]['last_served'][codename])
        assert(not (data[8000]['data'][codename] is
               data[8000]['last_served'][codename]))

    # Check tha codenams and sane_interval is set correctly
    assert(data[8000]['codenames'] == codenames)
    assert(data[8000]['sane_interval'] - 1.0 < 1E-8)

    live_socket.stop()

    print 'live init done'


def test_live_multiple_variables():
    codenames = ['name1', 'name2']
    live_socket = LiveSocket(codenames, 1.0)
    live_socket.start()

    HOST = "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    port = 8000

    # Test the 'codenames' command
    command = 'codenames'
    sock.sendto(command, (HOST, port))
    data, _ = sock.recvfrom(1024)
    expected = ['name1', 'name2']
    assert(json.loads(data) == expected)

    # Test the 'sane_interval' command
    sock.sendto('sane_interval', (HOST, port))
    data, _ = sock.recvfrom(1024)
    assert(json.loads(data) - 1.0 < 1E-8)

    for n in range(3):
        now = time.time()
        live_socket.set_point('name1', (now, n))
        live_socket.set_point('name2', (now, n+1))

        # Test the 'data' command
        sock.sendto('data', (HOST, port))
        data, _ = sock.recvfrom(1024)
        expected = [[now, n], [now, n+1]]
        assert(json.loads(data) == expected)

        time.sleep(0.1)

    live_socket.stop()

    print 'live multiple variables done'


def test_live_wrong_codename():
    codenames = ['name1', 'name2']
    live_socket = LiveSocket(codenames, 1.0)
    live_socket.start()

    # Test that trying to set an unknown name raises an exception
    with pytest.raises(ValueError):
        live_socket.set_point('bad name', (1, 2))

    live_socket.stop()

    print 'live wrong codename done'

#test_live_init()
#test_live_multiple_variables()
#test_live_wrong_codename()
#test_live_already_served()

# Common tests
def multiple_data_sockets(sockettype):
    """Test general functionality with multiple sockets

    This function is not directly executed by pytest.

    :param sockettype: The socket class under test
    """
    data_socket0 = sockettype(['meas0'], 9000)
    data_socket1 = sockettype( ['meas1'], 9001)
    data_socket0.start()
    data_socket1.start()
    
    HOST = "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Test for three points
    for n in range(3):
        now = time.time()
        data_socket0.set_point('meas0', (n, n+1))
        data_socket1.set_point('meas1', (n, now))

        # Test raw command
        command = 'raw'
        sock.sendto(command, (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto(command, (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = '{},{}'.format(n, n+1)
        expected1 = '{},{}'.format(n, now)
        assert(data0 == expected0)
        assert(data1 == expected1)

        # Test json command
        command = 'json'
        sock.sendto(command, (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto(command, (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = [[n, n+1]]
        expected1 = [[n, now]]
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        # Test raw_wn command (raw with names)
        command = 'raw_wn'
        sock.sendto(command, (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto(command, (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = 'meas0:{},{}'.format(n, n+1)
        expected1 = 'meas1:{},{}'.format(n, now)
        assert(data0 == expected0)
        assert(data1 == expected1)

        # Test json_wn command (json with names)
        command = 'json_wn'
        sock.sendto(command, (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto(command, (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = {'meas0': [n, n+1]}
        expected1 = {'meas1': [n, now]}
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        # Test codename#raw command
        sock.sendto('meas0#raw', (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto('meas1#raw', (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = '{},{}'.format(n, n+1)
        expected1 = '{},{}'.format(n, now)
        assert(data0 == expected0)
        assert(data1 == expected1)

        # Test codename#json command
        sock.sendto('meas0#json', (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto('meas1#json', (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = [n, n+1]
        expected1 = [n, now]
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        # Test codenames_raw command
        command = 'codenames_raw'
        sock.sendto(command, (HOST, 9000))
        data0, _ = sock.recvfrom(1024)
        sock.sendto(command, (HOST, 9001))
        data1, _ = sock.recvfrom(1024)
        expected0 = 'meas0'
        expected1 = 'meas1'
        assert(data0 == expected0)
        assert(data1 == expected1)

        # Test codenames_json command
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

    print 'multiple sockets done'


def multiple_variables(sockettype):
    """Test the general functionality with multiple measurements on a single
    socket

    This function is not executed directly by pytest.

    :param sockettype: The class under test
    """
    data_socket = sockettype(['one', 'two'])
    data_socket.start()

    # Test default port numbers
    if sockettype.__name__ == 'DateDataSocket':
        port = 9000
    elif sockettype.__name__ == 'DataSocket':
        port = 9010
    else:
        raise ValueError('Unknown class type')

    HOST = "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for n in range(3):
        now = time.time()
        data_socket.set_point('one', (n, n+1))
        data_socket.set_point('two', (n, now))

        # Test the raw command
        sock.sendto('raw', (HOST, port))
        data, _ = sock.recvfrom(1024)
        expected = '{},{};{},{}'.format(n, n+1, n, now)
        assert(data == expected)

        # Test the json command
        sock.sendto('json', (HOST, port))
        data, _ = sock.recvfrom(1024)
        expected = [[n, n+1], [n, now]]
        assert(json.loads(data) == expected)

        # Test the raw_wn command (raw with names)
        sock.sendto('raw_wn', (HOST, port))
        data, _ = sock.recvfrom(1024)
        expected = 'one:{},{};two:{},{}'.format(n, n+1, n, now)
        assert(expected == data)

        # Test the json_wn command (json with names)
        sock.sendto('json_wn', (HOST, port))
        data, _ = sock.recvfrom(1024)
        expected = {'one': [n, n+1], 'two': [n, now]}
        assert(expected == json.loads(data))

        # Test the codename#raw command
        sock.sendto('one#raw', (HOST, port))
        data0, _ = sock.recvfrom(1024)
        sock.sendto('two#raw', (HOST, port))
        data1, _ = sock.recvfrom(1024)
        expected0 = '{},{}'.format(n, n+1)
        expected1 = '{},{}'.format(n, now)
        assert(data0 == expected0)
        assert(data1 == expected1)

        # Test the codename#json command
        sock.sendto('one#json', (HOST, port))
        data0, _ = sock.recvfrom(1024)
        sock.sendto('two#json', (HOST, port))
        data1, _ = sock.recvfrom(1024)
        expected0 = [n, n+1]
        expected1 = [n, now]
        assert(json.loads(data0) == expected0)
        assert(json.loads(data1) == expected1)

        # Test the codenames_raw command
        command = 'codenames_raw'
        sock.sendto(command, (HOST, port))
        data, _ = sock.recvfrom(1024)
        expected = 'one,two'
        assert(data == expected)

        # Test the codenames_json command
        command = 'codenames_json'
        sock.sendto(command, (HOST, port))
        data, _ = sock.recvfrom(1024)
        expected = ['one', 'two']
        assert(json.loads(data) == expected)

        time.sleep(0.1)

    data_socket.stop()

    print 'multiple variables done'


def define_timeout(sockettype):
    """Test the definition of the timeouts and the cleaning up of data with
    stop

    This function is not executed directly by pytest.

    :param sockettype: The class under test
    """
    # Test one measurement with single timeout
    data_socket = sockettype(['one'], port=7000, timeouts=47)
    data_socket.start()
    assert(PyExpLabSys.common.sockets.DATA[7000]['timeouts'] == {'one': 47})
    data_socket.stop()
    assert(PyExpLabSys.common.sockets.DATA.get(7000) is None)
    del data_socket

    # Test one measurement with single timeout in list
    data_socket = sockettype(['one'], port=7000, timeouts=[47])
    data_socket.start()
    assert(PyExpLabSys.common.sockets.DATA[7000]['timeouts'] == {'one': 47})
    data_socket.stop()
    assert(PyExpLabSys.common.sockets.DATA.get(7000) is None)
    del data_socket

    # Test two measurements with single timeout
    data_socket = sockettype(['one', 'two'], port=7000, timeouts=42)
    data_socket.start()
    expected = {'one': 42, 'two': 42}
    assert(PyExpLabSys.common.sockets.DATA[7000]['timeouts'] == expected)
    data_socket.stop()
    assert(PyExpLabSys.common.sockets.DATA.get(7000) is None)
    del data_socket

    # Test two measurements with two timeouts in list
    data_socket = sockettype(['one', 'two'], port=7000, timeouts=[42, 47])
    data_socket.start()
    expected = {'one': 42, 'two': 47}
    assert(PyExpLabSys.common.sockets.DATA[7000]['timeouts'] == expected)
    data_socket.stop()
    assert(PyExpLabSys.common.sockets.DATA.get(7000) is None)
    del data_socket

    print 'define timeout done'

def data_timeout(sockettype, usetimestamp=False):
    data_socket = sockettype(['one', 'two'], timeouts=[0.1, 10], port=9000)
    data_socket.start()

    HOST = "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    now = time.time()
    if sockettype.__name__ == 'DateDataSocket':
        x1 = now
        x2 = now
        y1 = 42.0
        y2 = 47.0
    elif sockettype.__name__ == 'DataSocket':
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

    sock.sendto('raw', (HOST, 9000))
    data, _ = sock.recvfrom(1024)
    expected = '{};{},{}'.format('OLD_DATA', x2, y2)
    assert(data == expected)

    sock.sendto('json', (HOST, 9000))
    data, _ = sock.recvfrom(1024)
    expected = ['OLD_DATA', [x2, y2]]
    assert(json.loads(data) == expected)

    sock.sendto('raw_wn', (HOST, 9000))
    data, _ = sock.recvfrom(1024)
    expected = 'one:OLD_DATA;two:{},{}'.format(x2, y2)
    assert(expected == data)

    sock.sendto('json_wn', (HOST, 9000))
    data, _ = sock.recvfrom(1024)
    expected = {'one': 'OLD_DATA', 'two': [x2, y2]}
    assert(expected == json.loads(data))

    sock.sendto('one#raw', (HOST, 9000))
    data0, _ = sock.recvfrom(1024)
    sock.sendto('two#raw', (HOST, 9000))
    data1, _ = sock.recvfrom(1024)
    expected0 = 'OLD_DATA'
    expected1 = '{},{}'.format(x2, y2)
    assert(data0 == expected0)
    assert(data1 == expected1)

    sock.sendto('one#json', (HOST, 9000))
    data0, _ = sock.recvfrom(1024)
    sock.sendto('two#json', (HOST, 9000))
    data1, _ = sock.recvfrom(1024)
    expected0 = 'OLD_DATA'
    expected1 = [x2, y2]
    assert(json.loads(data0) == expected0)
    assert(json.loads(data1) == expected1)

    data_socket.stop()

    print 'multiple variables done'





