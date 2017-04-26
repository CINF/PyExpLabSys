""" The program will check up status of a list of hosts """
import subprocess
import datetime
import telnetlib
import socket
import threading
import Queue
import time
import json
import sys
import pickle
import os

CACHE_PATH = '/var/www/html/cache/'

def host_status(hostname, method=""):
    """ Report if a host i available on the network """
    host_is_up = True

    if method != 'rdp':
        try:
            subprocess.check_output(["ping", "-c1", "-W1", hostname])
        except subprocess.CalledProcessError:
            host_is_up = False
    if method == 'rdp':
        try:
            _ = telnetlib.Telnet(hostname, 3389)
        except socket.gaierror:
            host_is_up = False
        except socket.error:
            host_is_up = False
    return host_is_up

def uptime(hostname, method, username='pi', password='cinf123'):
    """ Fetch as much information as possible from a host """
    return_value = {}
    return_value['up'] = ''
    return_value['load'] = ''
    return_value['git'] = ''
    return_value['host_temperature'] = ''
    return_value['python_version'] = ''
    return_value['model'] = ''
    if method == 'ssh':
        uptime_string = subprocess.check_output(["sshpass",
                                                 "-p",
                                                 password,
                                                 "ssh",
                                                 '-o LogLevel=quiet',
                                                 '-oUserKnownHostsFile=/dev/null',
                                                 '-oStrictHostKeyChecking=no',
                                                 username + "@" + hostname,
                                                 'cat /proc/uptime /proc/loadavg'])
        uptime_raw = uptime_string.split('\n')[0]
        uptime_value = str(int(float(uptime_raw.split()[0]) / (60*60*24)))
        load = uptime_string.split('\n')[1].split()[2]
        return_value['up'] = uptime_value
        return_value['load'] = load

    ports = []
    for port_number in range(6000, 9999):
        ports.append(str(port_number)) # List of potential interesting ports
    if method in ['socket', 'ls'] + ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        port = 0
        if method == 'socket':
            port = 9000
        if method == 'ls':
            port = 8000
        if method in ports:
            port = int(method)

        try:
            sock.sendto('status', (hostname, port))
            
            received = sock.recv(4096)
            status = json.loads(received)
            system_status = status['system_status']
            return_value['sytem_status'] = system_status
            uptime_value = str(int(system_status['uptime']['uptime_sec']) / (60*60*24))
            load = str(system_status['load_average']['15m'])
            return_value['up'] = uptime_value
            return_value['load'] = load
        except:
            return_value['up'] = 'Down'
            return_value['load'] = 'Down'
        try:
            model = system_status['rpi_model']
            host_temperature = system_status['rpi_temperature']
        except (KeyError, UnboundLocalError):
            model = ''
            host_temperature = ''
        try:
            python_version = system_status['python_version']
        except (KeyError, UnboundLocalError):
            python_version = ''
        return_value['model'] = model
        return_value['host_temperature'] = host_temperature
        return_value['python_version'] = python_version
        try:
            gittime = system_status['last_git_fetch_unixtime']
            git = datetime.datetime.fromtimestamp(gittime).strftime('%Y-%m-%d')
        except TypeError:
            git = 'None'
        except  UnboundLocalError:
            git = ''
        return_value['git'] = git

        # If host has been determined to be down, we attempt to load from cache
        if return_value['up'] == 'Down':
            try:
                host_cache = pickle.load(open(CACHE_PATH + hostname + '.p', 'rb'))
                return_value['git'] = host_cache['git']
                return_value['model'] = host_cache['model']
                return_value['python_version'] = host_cache['python_version']
            except IOError:
                pass
        else: # Update cache
            pickle.dump(return_value, open(CACHE_PATH + hostname + '.p', 'wb'))
            #os.chmod(CACHE_PATH + hostname + '.p', 0777) # Halts when run as apache user....
    return return_value

class CheckHost(threading.Thread):
    """ Perfom the actual check """

    def __init__(self, hosts_queue, results_queue, return_all):
        threading.Thread.__init__(self)
        self.hosts = hosts_queue
        self.results = results_queue
        self.return_all = return_all

    def run(self):
        while not self.hosts.empty():
            host = self.hosts.get_nowait()
            host_is_up = host_status(host[0], host[2])
            if host_is_up:
                if host[1] == 'Raspberry Pi':
                    uptime_val = uptime(host[0], host[2])
                else:
                    uptime_val = uptime(host[0], host[2], username='cinf')
            else:
                uptime_val = {}
                uptime_val['up'] = ''
                uptime_val['load'] = ''
                uptime_val['git'] = ''
                uptime_val['host_temperature'] = ''
                uptime_val['model'] = ''
                uptime_val['python_version'] = ''
            if self.return_all:
                uptime_val['hostname'] = host[0]
                self.results.put(uptime_val)
            else:
                self.results.put([host[0], host_is_up, uptime_val['up'],
                                  uptime_val['load'], host[3],
                                  host[4], host[1],
                                  uptime_val['git'],
                                  uptime_val['host_temperature'],
                                  uptime_val['model'],
                                  uptime_val['python_version']])
            self.hosts.task_done()

def main(return_all=False):
    """ Main function """
    t = time.time()
    hosts = Queue.Queue()

    host_file = open('hosts.txt')
    lines = host_file.readlines()

    ok_lines = []
    for line in lines:
        line_is_ok = True
        if len(line.strip()) == 0: # Empty line
            line_is_ok = False
        if line.strip()[0] == '#': # Comment line
            line_is_ok = False
        if line_is_ok:
            ok_lines.append(line)

    for line in ok_lines:
        host_line = line.strip().split(',')
        for i in range(0, len(host_line)):
            host_line[i] = host_line[i].strip()
        hosts.put(host_line)

    results = Queue.Queue()
    t = time.time()
    host_checkers = {}
    for i in range(0, 20):
        host_checkers[i] = CheckHost(hosts, results, return_all)
        host_checkers[i].start()
    hosts.join()

    sorted_results = {}
    i = 0
    while not results.empty():
        i = i + 1
        result = results.get()
        sorted_results[i] = result

    status_string = ""
    for host in sorted_results.values():
        if return_all:
            status_string += json.dumps(host) + '\n'
        else:
            status_string += host[0] + "|"
            if host[1]:
                status_string += "1|"
                status_string += host[2] + "|"
                status_string += host[3] + "|"
            else:
                status_string += "0|||"
            status_string += host[4] + "|"
            status_string += host[5] + "|"
            status_string += host[6] + "|"
            status_string += host[7] + "|"
            status_string += str(host[8]) + "|"
            status_string += str(host[9]) + "|"
            status_string += host[10]
            status_string += "\n"
    print(status_string)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1] == 'True')
    else:
        main(False)
