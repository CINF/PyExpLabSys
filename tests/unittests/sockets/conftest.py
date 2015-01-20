# -*- coding: utf-8 -*-
"""File for pytest configuration and common fixtures"""

import pytest
import socket


@pytest.yield_fixture
def sock():
    """Client socket fixture"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    yield sock
    sock.close()