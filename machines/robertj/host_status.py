import subprocess
import datetime
import urllib2
import telnetlib
import socket
import signal
import threading
import Queue
import time
import json

def host_status(host,method=""):
    up = True
    
    if method != 'rdp':
        try:
            subprocess.check_output(["ping", "-c1", "-W1", host])
        except subprocess.CalledProcessError, e:
            up = False
    if method == 'rdp':
        try:
            f = telnetlib.Telnet(host,3389)
        except socket.gaierror,e:
            up = False
        except socket.error,e:
            up = False
    return up

def uptime(host, method, username='pi', password='cinf123'):
    return_value = {}
    return_value['up'] = ''
    return_value['load'] = ''
    return_value['git'] = ''
    return_value['host_temperature'] = ''
    return_value['model'] = ''
    if method == 'ssh':
        uptime_string = subprocess.check_output(["sshpass", 
                                                 "-p", 
                                                 password,
                                                 "ssh",
                                                 '-o LogLevel=quiet',
                                                 '-oUserKnownHostsFile=/dev/null',
                                                 '-oStrictHostKeyChecking=no',
                                                 username + "@" + host, 
                                                 'cat /proc/uptime /proc/loadavg'])
        uptime = uptime_string.split('\n')[0]
        up = str(int(float(uptime.split()[0]) / (60*60*24)))
        load = uptime_string.split('\n')[1].split()[2]
        return_value['up'] = up
        return_value['load'] = load

    if method in ['socket', 'ls']:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.1)
        port = 0
        port = 9000 if method == 'socket' else port
        port = 8000 if method == 'ls' else port
        try:
            sock.sendto('status', (host, port))
            received = sock.recv(1024)
            status = json.loads(received)
            system_status = status['system_status']
            up = str(int(system_status['uptime']['uptime_sec']) / (60*60*24))
            load = str(system_status['load_average']['15m'])
            return_value['up'] = up
            return_value['load'] = load
        except:
            return_value['up'] = 'Down'
            return_value['load'] = 'Down'
        try:
            model = system_status['rpi_model']
            host_temperature = system_status['rpi_temperatur']
        except (KeyError, UnboundLocalError) as e:
            model = ''
            host_temperature = ''
        return_value['model'] = model
        return_value['host_temperature'] = host_temperature
        try:
            gittime = system_status['last_git_fetch_unixtime']
            git = datetime.datetime.fromtimestamp(gittime).strftime('%Y-%m-%d')
        except TypeError:
            git = 'None'
        except  UnboundLocalError:
            git = ''
        return_value['git'] = git
    """
    Will need to modify uptime script on these hosts...
    if method== 'http':
        f = urllib2.urlopen('http://' + host + '/uptime.php')
        uptime_string = f.read()
        f.close()
    """
    return return_value


class CheckHost(threading.Thread):

    def __init__(self, hosts_queue, results_queue):
        threading.Thread.__init__(self)
        self.hosts = hosts
        self.results = results_queue

    def run(self):
        while not self.hosts.empty():
            host = hosts.get_nowait()
            up = host_status(host[0],host[2])
            if up:
                if host[1] == 'Raspberry Pi':
                    uptime_val = uptime(host[0],host[2])
                else:
                    uptime_val = uptime(host[0],host[2], username='cinf')
            else:
                uptime_val = {}
                uptime_val['up'] = ''
                uptime_val['load'] = ''
                uptime_val['git'] = ''
                uptime_val['host_temperature'] = ''
                uptime_val['model'] = ''
            self.results.put([host[0], up, uptime_val['up'],
                              uptime_val['load'], host[3],
                              host[4], host[1],
                              uptime_val['git'],
                              uptime_val['host_temperature'],
                              uptime_val['model']])
            self.hosts.task_done()

if __name__ == "__main__":
    t = time.time()
    hosts = Queue.Queue()

    host_file = open('hosts.txt')
    lines = host_file.readlines()

    ok_lines = []
    for line in lines:
        ok = True
        if len(line.strip()) == 0:
            ok = False            
        if line.strip()[0] == '#':
            ok = False
        if ok:
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
        host_checkers[i] = CheckHost(hosts, results)
        host_checkers[i].start()
    hosts.join()

    sorted_results = {}
    while not results.empty():
        result = results.get()
        sorted_results[result[0]] = result

    status_string = ""
    for host in sorted_results.values():
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
        status_string += host[9]
        status_string += "\n"
    print(status_string)
