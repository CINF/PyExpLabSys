"""This module contains the SystemStatus class"""

import os
import sys
import threading


class SystemStatus(object):
    """Class that fetches set of system status information"""

    def __init__(self):
        # Form the list of which items to measure on different platforms
        self.platform = sys.platform
        self.all_list = ['last_git_fetch_unixtime',
                         'number_of_python_threads']
        if self.platform == 'linux2':
            import resource
            self.resource = resource
            self.all_list += ['uptime', 'last_apt_cache_change_unixtime',
                              'load_average', 'filesystem_usage',
                              'max_python_mem_usage_bytes']

    def complete_status(self):
        """Returns all system status information items as a dictionary"""
        all_items = {}
        for item in self.all_list:
            all_items[item] = getattr(self, item)()
        return all_items

    # All platforms
    def last_git_fetch_unixtime(self):
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
    def number_of_python_threads():
        """Returns the number of threads in Python"""
        return threading.activeCount()

    # Linux only
    @staticmethod
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
    def last_apt_cache_change_unixtime():
        """Returns the unix timestamp of the last apt-get upgrade"""
        apt_cache_dir = '/var/cache/apt'
        if os.access(apt_cache_dir, os.F_OK):
            return os.path.getmtime('/proc/uptime')
        else:
            return None

    @staticmethod
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
    def filesystem_usage():
        """Return the total and free number of bytes in the current filesystem
        """
        statvfs = os.statvfs(__file__)
        status = {
            'total_bytes': statvfs.f_frsize * statvfs.f_blocks,
            'free_bytes': statvfs.f_frsize * statvfs.f_bfree
        }
        return status

    def max_python_mem_usage_bytes(self):
        """Returns the python memory usage"""
        pagesize = self.resource.getpagesize()
        this_process = self.resource.getrusage(
            self.resource.RUSAGE_SELF).ru_maxrss
        children = self.resource.getrusage(
            self.resource.RUSAGE_CHILDREN).ru_maxrss
        return (this_process + children) * pagesize
