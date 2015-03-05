# -*- coding: utf-8 -*-
# pylint: disable=no-member, redefined-outer-name, no-self-use
# pylint: disable=too-many-statements, star-args

# NOTE: About pylint disable. Everything on line one are for checks that
# simply makes no sense when using pytest and fixtures

"""Unittests for the sockets code

NOTE: The sock fixture used in this module is defined in the conftest.py
"""

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
DATA = PyExpLabSys.common.sockets.DATA
from PyExpLabSys.common.sockets import DataPullSocket, DateDataPullSocket

#from PyExpLabSys.common.utilities import get_logger
#LOGGER = get_logger('Test data socket', level='info')


# Module variables
HOST = '127.0.0.1'
NAME = 'Usage statistics from giant moon laser'
DEFAULT_PORTS = {
    DateDataPullSocket: 9000,
    DataPullSocket: 9010,
}
DEFAULT_CODENAMES = ['Laser1', 'Laser2']


# Test fixtures
@pytest.fixture(
    params=[
        (DataPullSocket, False),
        (DataPullSocket, True),
        (DateDataPullSocket, False),
    ],
    ids=[
        'DataPullSocket',
        'DataPullSocket_use_timestamp',
        'DateDataPullSocket',
    ]
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
    for index in range(3):
        now = time.time()
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

    for index in range(3):
        now = time.time()
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

        time.sleep(0.1)
    data_socket.stop()


def test_cleanup(sockettype):
    """Test the definition of the timeouts and the cleaning up of data with
    stop"""
    # Test one measurement with single timeout
    data_socket = sockettype(NAME, DEFAULT_CODENAMES)
    data_socket.start()
    data_socket.stop()
    assert PyExpLabSys.common.sockets.DATA.get(7000) is None


def test_data_timeout(socket_and_use_timestamp, sock):
    """Test the data timeout functionality"""
    sockettype, usetimestamp = socket_and_use_timestamp
    data_socket = sockettype(NAME, ['one', 'two'], timeouts=[0.1, 10],
                             port=9000)
    data_socket.start()

    now = time.time()
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
        data_socket.set_point('one', point1)
        data_socket.set_point('two', point2)

    time.sleep(0.15)  # Obsoletes the first point

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

    data_socket.stop()


class TestInit(object):
    """Class that wraps test of successful initialization"""

    def test_defaults(self, sockettype):
        """Test of default values on init"""
        # Setup
        pullsocket = sockettype(NAME, DEFAULT_CODENAMES)
        pullsocket.start()
        port = DEFAULT_PORTS[pullsocket.__class__]

        # Test initialization of data dict
        # Keys at base level
        assert isinstance(DATA.get(port), dict)
        keynames = ['activity', 'codenames', 'data', 'name', 'timeouts',
                    'type']
        if pullsocket.__class__.__name__ == 'DataPullSocket':
            keynames.insert(5, 'timestamps')
        assert sorted(DATA[port].keys()) == keynames

        # activity
        assert isinstance(DATA[port]['activity'], dict)
        assert sorted(DATA[port]['activity']) == \
            ['activity_timeout', 'check_activity', 'last_activity']
        assert DATA[port]['activity']['check_activity'] is True
        # activity values
        assert DATA[port]['activity']['activity_timeout'] == 900

        # codenames
        assert isinstance(DATA[port]['codenames'], list)
        # codename values
        assert DATA[port]['codenames'] == DEFAULT_CODENAMES

        # data
        assert isinstance(DATA[port]['data'], dict)
        # default data values
        for name in DEFAULT_CODENAMES:
            assert isinstance(DATA[port]['data'][name], tuple)
            assert DATA[port]['data'][name] == (0.0, 0.0)

        # name
        assert isinstance(DATA[port]['name'], str)
        # name value
        assert DATA[port]['name'] == NAME

        # timeouts
        assert isinstance(DATA[port]['timeouts'], dict)
        # timeouts values
        for name in DEFAULT_CODENAMES:
            assert DATA[port]['timeouts'][name] is None

        # timestamps
        if pullsocket.__class__.__name__ == 'DataPullSocket':
            assert isinstance(DATA[port]['timestamps'], dict)
            # timestamps values
            for name in DEFAULT_CODENAMES:
                assert DATA[port]['timestamps'][name] == 0.0

        # type
        assert isinstance(DATA[port]['type'], str)
        if pullsocket.__class__.__name__ == 'DataPullSocket':
            assert DATA[port]['type'] == 'data'
        else:
            assert DATA[port]['type'] == 'date'

        # port
        assert len(DATA.keys()) == 1
        assert isinstance(DATA.keys()[0], int)
        assert DATA.keys()[0] == port

        # Tear down
        pullsocket.stop()

    def test_port(self, sockettype):
        """Test initialization with custom port"""
        pullsocket = sockettype(NAME, DEFAULT_CODENAMES, port=4747)
        pullsocket.start()
        assert len(DATA.keys()) == 1
        assert isinstance(DATA.keys()[0], int)
        assert DATA.keys()[0] == 4747
        pullsocket.stop()

    def test_default_values(self, sockettype):
        """Test the default x and y values"""
        pullsocket = sockettype(NAME, DEFAULT_CODENAMES,
                                default_x=42.0, default_y=47.0)
        port = DEFAULT_PORTS[pullsocket.__class__]
        pullsocket.start()
        for name in DEFAULT_CODENAMES:
            assert DATA[port]['data'][name] == (42.0, 47.0)
        pullsocket.stop()

    def test_timeouts(self, sockettype):
        """Test initializatin of custom timeouts"""
        # For combinations of defining one or more measurements
        for codenames in [DEFAULT_CODENAMES[:1], DEFAULT_CODENAMES]:
            # Test defining one default timeout outside of list
            pullsocket = sockettype(NAME, codenames, timeouts=47)
            port = DEFAULT_PORTS[pullsocket.__class__]
            pullsocket.start()
            expected_timeouts = dict([[cn, 47] for cn in codenames])
            assert DATA[port]['timeouts'] == expected_timeouts
            pullsocket.stop()

            # Test defining one or more defaults in a list
            if len(codenames) == 1:
                timeouts = [47]
            else:
                timeouts = [47, 42]
            pullsocket = sockettype(NAME, codenames, timeouts=timeouts)
            port = DEFAULT_PORTS[pullsocket.__class__]
            pullsocket.start()
            expected_timeouts = dict(zip(codenames, timeouts))
            assert DATA[port]['timeouts'] == expected_timeouts
            pullsocket.stop()

    def test_check_activity(self, sockettype):
        """Test settings the check_activity value"""
        pullsocket = sockettype(NAME, DEFAULT_CODENAMES, check_activity=False)
        port = DEFAULT_PORTS[pullsocket.__class__]
        pullsocket.start()
        assert DATA[port]['activity']['check_activity'] is False
        pullsocket.stop()

    def test_activity_timeout(self, sockettype):
        """Test settings the check_activity value"""
        pullsocket = sockettype(NAME, DEFAULT_CODENAMES, activity_timeout=47.0)
        port = DEFAULT_PORTS[pullsocket.__class__]
        pullsocket.start()
        assert DATA[port]['activity']['activity_timeout'] == 47.0
        pullsocket.stop()
