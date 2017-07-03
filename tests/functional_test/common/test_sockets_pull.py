"""Functional tests for the PyExpLabSys.common.sockets module"""

# Built-in imports
import time
import json
import socket
try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer
# Allow for fast restart of a socket on a port for test purposes
SocketServer.UDPServer.allow_reuse_address = True

# Extra modules
import mock
import pytest
# Own imports
import PyExpLabSys.common.sockets
DATA = PyExpLabSys.common.sockets.DATA
from PyExpLabSys.common.sockets import DataPullSocket, DateDataPullSocket
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


# Module variables
HOST = '127.0.0.1'
NAME = 'Usage statistics from giant moon laser'
DEFAULT_PORTS = {
    DateDataPullSocket: 9000,
    DataPullSocket: 9010,
}
DEFAULT_CODENAMES = ['Laser1', 'Laser2']


@pytest.yield_fixture
def sock():
    """Client socket fixture"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    yield sock
    sock.close()


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
    sock.sendto(command.encode('ascii'), (HOST, port))
    data, _ = sock.recvfrom(1024)
    data = data.decode('ascii')
    return data


# Common tests
def test_multiple_data_sockets(sockettype, sock):
    """Test general functionality with multiple sockets"""
    data_socket0 = sockettype(NAME + '1', ['meas0'], 9000)
    data_socket1 = sockettype(NAME + '2', ['meas1'], 9001)
    data_socket0.start()
    data_socket1.start()

    start_time = time.time()

    # Test for three points
    for index in range(3):
        now = start_time + index  # Fake time
        data_socket0.set_point('meas0', (index, index + 1))
        data_socket1.set_point('meas1', (index, now))

        # Test raw command
        data0 = send_and_resc(sock, 'raw', 9000)
        data1 = send_and_resc(sock, 'raw', 9001)
        expected0 = '{},{}'.format(index, index + 1)
        expected1 = '{},{}'.format(index, now)
        assert data0 == expected0
        assert data1 == expected1

        # Test json command
        data0 = send_and_resc(sock, 'json', 9000)
        data1 = send_and_resc(sock, 'json', 9001)
        expected0 = [[index, index + 1]]
        expected1 = [[index, now]]
        assert json.loads(data0) == expected0
        assert json.loads(data1) == expected1

        # Test raw_wn command (raw with names)
        data0 = send_and_resc(sock, 'raw_wn', 9000)
        data1 = send_and_resc(sock, 'raw_wn', 9001)
        expected0 = 'meas0:{},{}'.format(index, index + 1)
        expected1 = 'meas1:{},{}'.format(index, now)
        assert data0 == expected0
        assert data1 == expected1

        # Test json_wn command (json with names)
        data0 = send_and_resc(sock, 'json_wn', 9000)
        data1 = send_and_resc(sock, 'json_wn', 9001)
        expected0 = {'meas0': [index, index + 1]}
        expected1 = {'meas1': [index, now]}
        assert json.loads(data0) == expected0
        assert json.loads(data1) == expected1

        # Test codename#raw command
        data0 = send_and_resc(sock, 'meas0#raw', 9000)
        data1 = send_and_resc(sock, 'meas1#raw', 9001)
        expected0 = '{},{}'.format(index, index + 1)
        expected1 = '{},{}'.format(index, now)
        assert data0 == expected0
        assert data1 == expected1

        # Test codename#json command
        data0 = send_and_resc(sock, 'meas0#json', 9000)
        data1 = send_and_resc(sock, 'meas1#json', 9001)
        expected0 = [index, index + 1]
        expected1 = [index, now]
        assert json.loads(data0) == expected0
        assert json.loads(data1) == expected1

        # Test codenames_raw command
        command = 'codenames_raw'
        data0 = send_and_resc(sock, command, 9000)
        data1 = send_and_resc(sock, command, 9001)
        expected0 = 'meas0'
        expected1 = 'meas1'
        assert data0 == expected0
        assert data1 == expected1

        # Test codenames_json command
        command = 'codenames_json'
        data0 = send_and_resc(sock, command, 9000)
        data1 = send_and_resc(sock, command, 9001)
        expected0 = ['meas0']
        expected1 = ['meas1']
        assert json.loads(data0) == expected0
        assert json.loads(data1) == expected1

    with mock.patch('time.sleep'):
        data_socket0.stop()
        data_socket1.stop()

    # Test cleanup
    assert 9000 not in PyExpLabSys.common.sockets.DATA
    assert 9001 not in PyExpLabSys.common.sockets.DATA


def test_multiple_variables(sockettype, sock):
    """Test the general functionality with multiple measurements on a single socket"""
    data_socket = sockettype(NAME, ['one', 'two'])
    data_socket.start()

    # Test default port numbers
    if sockettype.__name__ == 'DateDataPullSocket':
        port = 9000
    elif sockettype.__name__ == 'DataPullSocket':
        port = 9010
    else:
        raise ValueError('Unknown class type')

    start_time = time.time()

    for index in range(3):
        now = start_time + index  # Fake time
        data_socket.set_point('one', (index, index + 1))
        data_socket.set_point('two', (index, now))

        # Test the raw command
        data = send_and_resc(sock, 'raw', port)
        expected = '{},{};{},{}'.format(index, index + 1, index, now)
        assert data == expected

        # Test the json command
        data = send_and_resc(sock, 'json', port)
        expected = [[index, index + 1], [index, now]]
        assert json.loads(data) == expected

        # Test the raw_wn command (raw with names)
        data = send_and_resc(sock, 'raw_wn', port)
        expected = 'one:{},{};two:{},{}'.format(index, index + 1, index, now)
        assert expected == data

        # Test the json_wn command (json with names)
        data = send_and_resc(sock, 'json_wn', port)
        expected = {'one': [index, index + 1], 'two': [index, now]}
        assert expected == json.loads(data)

        # Test the codename#raw command
        data0 = send_and_resc(sock, 'one#raw', port)
        data1 = send_and_resc(sock, 'two#raw', port)
        expected0 = '{},{}'.format(index, index + 1)
        expected1 = '{},{}'.format(index, now)
        assert data0 == expected0
        assert data1 == expected1

        # Test the codename#json command
        data0 = send_and_resc(sock, 'one#json', port)
        data1 = send_and_resc(sock, 'two#json', port)
        expected0 = [index, index + 1]
        expected1 = [index, now]
        assert json.loads(data0) == expected0
        assert json.loads(data1) == expected1

        # Test the codenames_raw command
        data = send_and_resc(sock, 'codenames_raw', port)
        expected = 'one,two'
        assert data == expected

        # Test the codenames_json command
        data = send_and_resc(sock, 'codenames_json', port)
        expected = ['one', 'two']
        assert json.loads(data) == expected

    with mock.patch('time.sleep'):
        data_socket.stop()

    # Test clean up
    assert port not in PyExpLabSys.common.sockets.DATA


def test_data_timeout(socket_and_use_timestamp, sock):
    """Test the data timeout functionality"""
    sockettype, usetimestamp = socket_and_use_timestamp
    data_socket = sockettype(NAME, ['one', 'two'], timeouts=[0.1, 10],
                             port=9000)
    data_socket.start()

    # Pretend that these points were logged 0.15 seconds ago, to trip the old data check
    now = time.time() - 0.15
    if sockettype.__name__ == 'DateDataPullSocket':
        point1 = (now, 42.0)
        point2 = (now, 47.0)
    elif sockettype.__name__ == 'DataPullSocket':
        point1 = (9.7, 100)
        point2 = (15.3, 111)
    else:
        raise ValueError('Unknown class type')

    if usetimestamp:
        data_socket.set_point('one', point1, timestamp=now)
        data_socket.set_point('two', point2, timestamp=now)

    else:
        # Mock time, to pretend that these points were logged 0.15 seconds ago, also in the
        # case where it gets the time internally
        with mock.patch('time.time') as time_:
            time_.return_value = now
            data_socket.set_point('one', point1)
            data_socket.set_point('two', point2)

    data = send_and_resc(sock, 'raw', 9000)
    expected = '{};{},{}'.format('OLD_DATA', *point2)
    assert data == expected

    data = send_and_resc(sock, 'json', 9000)
    expected = ['OLD_DATA', list(point2)]
    assert json.loads(data) == expected

    data = send_and_resc(sock, 'raw_wn', 9000)
    expected = 'one:OLD_DATA;two:{},{}'.format(*point2)
    assert expected == data

    data = send_and_resc(sock, 'json_wn', 9000)
    expected = {'one': 'OLD_DATA', 'two': list(point2)}
    assert expected == json.loads(data)

    data0 = send_and_resc(sock, 'one#raw', 9000)
    data1 = send_and_resc(sock, 'two#raw', 9000)
    expected0 = 'OLD_DATA'
    expected1 = '{},{}'.format(*point2)
    assert data0 == expected0
    assert data1 == expected1

    data0 = send_and_resc(sock, 'one#json', 9000)
    data1 = send_and_resc(sock, 'two#json', 9000)
    expected0 = 'OLD_DATA'
    expected1 = list(point2)
    assert json.loads(data0) == expected0
    assert json.loads(data1) == expected1

    with mock.patch('time.sleep'):
        data_socket.stop()
