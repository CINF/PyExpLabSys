# pylint: disable=global-statement

"""Module that runs an ssh tunnel the background"""

import subprocess
import socket
import fcntl
import struct


TUNNEL = None


def create_tunnel():
    """Create a SSH tunnel to demon.fysik.dtu.dk"""
    global TUNNEL
    if TUNNEL != None:
        return False
    TUNNEL = subprocess.Popen(
        'ssh -L 9000:servcinf-sql:3306 fridays@demon.fysik.dtu.dk', shell=True,
        stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    return True


def close_tunnel():
    """Close the SSH tunnel to demon.fysik.dtu.dk"""
    global TUNNEL

    if TUNNEL is None:
        return False

    try:
        TUNNEL.poll()
        TUNNEL.terminate()
        TUNNEL.wait()
    except:  # pylint: disable=bare-except
        pass
    TUNNEL = None

    return True


def get_ip_address():
    """Returns the IP address of either the eth0 or the wlan0 interface.

    Will try the eth0 interface first, and if that succeeds return that value.
    Only if it fails will it attempt the wlan0 interface. Will return None if
    neither succeeds.
    """
    eth0_ip = get_ip_address_of_interface('eth0')
    if eth0_ip is not None:
        return 'eth0', eth0_ip

    wlan0_ip = get_ip_address_of_interface('wlan0')
    if wlan0_ip is not None:
        return 'wlan0', wlan0_ip

    return None, None


def get_ip_address_of_interface(ifname):
    """Returns the IP address of a specific interface

    Interface can be e.g. 'eth0' or 'wlan0'
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        return socket.inet_ntoa(fcntl.ioctl(
            sock.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24])
    except IOError:
        return None


def test_demon_connection():
    """Test if there is connection to the demon.fysik.dtu.dk server"""
    status = subprocess.call(["/bin/ping", "-c1", "-w100", "demon.fysik.dtu.dk"])
    if status == 0:
        return True
    else:
        return False
