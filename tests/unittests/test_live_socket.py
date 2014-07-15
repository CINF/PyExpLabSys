# -*- coding: utf-8 -*-
"""Test the LiveSocket """

import time
import json
import pytest
import PyExpLabSys.common.sockets
from PyExpLabSys.common.sockets import LiveSocket

# Module variables
HOST = '127.0.0.1'
NAME = 'Usage statistics from giant moon laser'


def send_and_resc(sock, command, port):
    """Helper UPD socket send and receive"""
    sock.sendto(command, (HOST, port))
    data, _ = sock.recvfrom(1024)
    return data


### LiveSocket test
def test_live_init():
    codenames = ['name1', 'name2']
    live_socket = LiveSocket(NAME, codenames, 1.0)
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


def test_live_multiple_variables(sock):
    codenames = ['name1', 'name2']
    live_socket = LiveSocket(NAME, codenames, 1.0)
    live_socket.start()

    port = 8000

    # Test the 'codenames' command
    data = send_and_resc(sock, 'codenames', port)
    expected = ['name1', 'name2']
    assert(json.loads(data) == expected)

    # Test the 'sane_interval' command
    data = send_and_resc(sock, 'sane_interval', port)
    assert(json.loads(data) - 1.0 < 1E-8)

    for n in range(3):
        now = time.time()
        live_socket.set_point('name1', (now, n))
        live_socket.set_point('name2', (now, n+1))

        # Test the 'data' command
        data = send_and_resc(sock, 'data', port)
        expected = [[now, n], [now, n+1]]
        assert(json.loads(data) == expected)

        time.sleep(0.1)

    live_socket.stop()


def test_live_wrong_codename():
    codenames = ['name1', 'name2']
    live_socket = LiveSocket(NAME, codenames, 1.0)
    live_socket.start()

    # Test that trying to set an unknown name raises an exception
    with pytest.raises(ValueError):
        live_socket.set_point('bad name', (1, 2))

    live_socket.stop()
