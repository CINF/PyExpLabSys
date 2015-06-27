"""This module contains the SystemStatus class

This module is Python 2 and 3 compatible.
"""

from __future__ import unicode_literals
import os
import re
import sys
import socket
import fcntl
import struct
import threading
import subprocess
try:
    import resource
except ImportError:
    resource = None  # pylint: disable=C0103

# Source: http://www.raspberrypi-spy.co.uk/2012/09/checking-your-raspberry-pi-board-version/
RPI_REVISIONS = {
    '0002': 'Model B Revision 1.0',
    '0003': 'Model B Revision 1.0 + ECN0001 (no fuses, D14 removed)',
    '0004': 'Model B Revision 2.0 Mounting holes',
    '0005': 'Model B Revision 2.0 Mounting holes',
    '0006': 'Model B Revision 2.0 Mounting holes',
    '0007': 'Model A Mounting holes',
    '0008': 'Model A Mounting holes',
    '0009': 'Model A Mounting holes',
    '000d': 'Model B Revision 2.0 Mounting holes',
    '000e': 'Model B Revision 2.0 Mounting holes',
    '000f': 'Model B Revision 2.0 Mounting holes',
    '0010': 'Model B+',
    '0011': 'Compute Module',
    '0012': 'Model A+',
    'a01041': 'Pi 2 Model B',
    'a21041': 'Pi 2 Model B',
}
# Temperature regular expression
RPI_TEMP_RE = re.compile(r"temp=([0-9\.]*)'C")


def works_on(platform):
    """Return a decorator that attaches a _works_on (platform) attribute to methods"""
    def decorator(function):
        """Decorate a method with a _works_on attribute"""
        function._works_on = platform  # pylint: disable=protected-access
        return function
    return decorator


class SystemStatus(object):
    """Class that fetches set of system status information"""

    def __init__(self):
        # Form the list of which items to measure on different platforms
        if 'linux' in sys.platform:
            platforms = {'all', 'linux', 'linux2'}
        else:
            platforms = {'all', sys.platform}

        # Form the list methods that work in this platform, using the _works_on attribute
        # that is appended with a decorator
        self.methods_on_this_platform = []
        for attribute_name in dir(self):
            method = getattr(self, attribute_name)
            # pylint: disable=W0212
            if hasattr(method, '_works_on') and method._works_on in platforms:
                self.methods_on_this_platform.append(method)

    def complete_status(self):
        """Returns all system status information items as a dictionary"""
        return {method.__name__: method() for method in self.methods_on_this_platform}

    # All platforms
    @staticmethod
    @works_on('all')
    def last_git_fetch_unixtime():
        """Returns the unix timestamp and author time zone offset in seconds of
        the last git commit
        """
        # Get dirname of current file and add two parent directory entries a
        # .git and a FETCH_HEAD in a hopefullt crossplatform manner, result:
        # /home/pi/PyExpLabSys/PyExpLabSys/common/../../.git/FETCH_HEAD
        fetch_head_file = os.path.join(
            os.path.dirname(__file__),
            *[os.path.pardir] * 2 + ['.git', 'FETCH_HEAD']
        )
        # Check for last change
        if os.access(fetch_head_file, os.F_OK):
            return os.path.getmtime(fetch_head_file)
        else:
            return None

    @staticmethod
    @works_on('all')
    def number_of_python_threads():
        """Returns the number of threads in Python"""
        return threading.activeCount()

    @staticmethod
    @works_on('all')
    def python_version():
        """Returns the Python version"""
        return '{}.{}.{}'.format(*sys.version_info)

    # Linux only
    @staticmethod
    @works_on('linux2')
    def uptime():
        """Returns the system uptime"""
        sysfile = '/proc/uptime'
        if os.access(sysfile, os.R_OK):
            with open(sysfile, 'r') as file_:
                # Line looks like: 10954694.52 10584141.11
                line = file_.readline()
            names = ['uptime_sec', 'idle_sec']
            values = [float(value) for value in line.split()]
            return dict(zip(names, values))
        else:
            return None

    @staticmethod
    @works_on('linux2')
    def last_apt_cache_change_unixtime():
        """Returns the unix timestamp of the last apt-get upgrade"""
        apt_cache_dir = '/var/cache/apt'
        if os.access(apt_cache_dir, os.F_OK):
            return os.path.getmtime('/proc/uptime')
        else:
            return None

    @staticmethod
    @works_on('linux2')
    def load_average():
        """Returns the system load average"""
        sysfile = '/proc/loadavg'
        if os.access(sysfile, os.R_OK):
            with open(sysfile, 'r') as file_:
                line = file_.readline()
            # The line looks like this:
            # 0.41 0.33 0.26 1/491 21659
            loads = (float(load) for load in line.split()[0:3])
            return dict(zip(['1m', '5m', '15m'], loads))
        else:
            return None

    @staticmethod
    @works_on('linux2')
    def filesystem_usage():
        """Return the total and free number of bytes in the current filesystem
        """
        statvfs = os.statvfs(__file__)
        status = {
            'total_bytes': statvfs.f_frsize * statvfs.f_blocks,
            'free_bytes': statvfs.f_frsize * statvfs.f_bfree
        }
        return status

    @staticmethod
    @works_on('linux2')
    def max_python_mem_usage_bytes():
        """Returns the python memory usage"""
        pagesize = resource.getpagesize()
        this_process = resource.getrusage(
            resource.RUSAGE_SELF).ru_maxrss
        children = resource.getrusage(
            resource.RUSAGE_CHILDREN).ru_maxrss
        return (this_process + children) * pagesize

    @staticmethod
    @works_on('linux2')
    def mac_address():
        """Return the mac address of eth0"""
        ifname = b'eth0'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        info = fcntl.ioctl(sock.fileno(), 0x8927, struct.pack(b'256s', ifname[:15]))
        if sys.version < '3':
            return ':'.join(['%02x' % ord(char) for char in info[18:24]])
        else:
            return ':'.join(['%02x' % char for char in info[18:24]])

    @staticmethod
    @works_on('linux2')
    def rpi_model():
        """Return the Raspberry Pi"""
        with open('/proc/cpuinfo') as file_:
            for line in file_:
                if line.startswith('Revision'):
                    # The line looks like this:
                    #Revision         : 0002
                    revision = line.strip().split(': ')[1]
                    break
            else:
                return None

        return RPI_REVISIONS.get(revision, 'Undefined revision')

    @staticmethod
    @works_on('linux2')
    def rpi_temperature():
        """Return the temperature of a Raspberry Pi"""
        # Get temperature string
        try:
            temp_str = subprocess.check_output(['cat',
                                                '/sys/class/thermal/thermal_zone0/temp'])
        except OSError:
            return None

        # Temperature string simply returns temperature in milli-celcius
        temp = float(temp_str) / 1000
        return temp

    @staticmethod
    @works_on('linux2')
    def sd_card_serial():
        """Return the SD card serial number"""
        try:
            with open('/sys/block/mmcblk0/device/cid') as file_:
                serial = file_.read().strip()
            return serial
        except IOError:
            return None


if __name__ == '__main__':
    from pprint import pprint
    SYSTEM_STATUS = SystemStatus()
    pprint(SYSTEM_STATUS.complete_status())
