import subprocess
import urllib2
import telnetlib
import socket
import signal
import threading
import Queue
import time

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
    uptime_string = ""
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
    """
    Will need to modify uptime script on these hosts...
    if method== 'http':
        f = urllib2.urlopen('http://' + host + '/uptime.php')
        uptime_string = f.read()
        f.close()
    """
    if uptime_string!="":
        uptime = uptime_string.split('\n')[0]
        up = str(int(float(uptime.split()[0]) / (60*60*25)))
        load = uptime_string.split('\n')[1].split()[2]
        return_value = [up, load]
    else:
        return_value = ['', '']
    return return_value


class CheckHost(threading.Thread):

    def __init__(self, hosts_queue, results_queue):
        threading.Thread.__init__(self)
        self.hosts = hosts
        self.results = results_queue

    def run(self):
        while not self.hosts.empty():
            host = hosts.get_nowait()
            print host
            up = host_status(host[0],host[2])
            if up:
                uptime_val = uptime(host[0],host[2])
            else:
                uptime_val = ['', '']
            self.results.put([host[0], up, uptime_val[0], uptime_val[1], host[3], host[1]])
            self.hosts.task_done()

if __name__ == "__main__":
    t = time.time()
    hosts = Queue.Queue()
    hosts.put(['rasppi00','Raspberry Pi','ssh','STM312 - X-ray cooling water flow'])
    hosts.put(['rasppi01','Raspberry Pi','ssh','TOF Pressure'])
    hosts.put(['rasppi04','Raspberry Pi','ssh','Volvo pressure readout'])
    hosts.put(['rasppi05','Raspberry Pi','ssh','Microreactors, temperature control'])
    hosts.put(['rasppi06','Raspberry Pi','ssh','Webcams'])
    hosts.put(['rasppi08','Raspberry Pi','ssh','Old CS, TC and pressure readout '])
    hosts.put(['rasppi09','Raspberry Pi','ssh','NH3 - Pressure readout'])
    hosts.put(['rasppi12','Raspberry Pi','ssh','Microreactors TC-readout'])         
    hosts.put(['rasppi13','Raspberry Pi','ssh','STM 312, Flow controllers'])         
    hosts.put(['rasppi14','Raspberry Pi','ssh','NH3 concentration + temperature'])
    hosts.put(['rasppi15','Raspberry Pi','ssh','Gasmonitor, B312'])
    hosts.put(['rasppi16','Raspberry Pi','ssh','Microreactor NG, Flows'])
    hosts.put(['rasppi17','Raspberry Pi','ssh','Microreactor, Mass Spectrometer'])
    hosts.put(['rasppi19','Raspberry Pi','ssh','STM 312, Temperature control'])         
    hosts.put(['rasppi20','Raspberry Pi','ssh','STM 312 + PS chillers'])
    hosts.put(['rasppi21','Raspberry Pi','ssh','Sputterchamber'])
    hosts.put(['rasppi22','Raspberry Pi','ssh','Bakeout control box - STM312'])
    hosts.put(['rasppi24','Raspberry Pi','ssh','Old Microreactor - flow controllers'])
    hosts.put(['rasppi25','Raspberry Pi','ssh','Datalogger thetaprobe'])
    hosts.put(['rasppi27','Raspberry Pi','ssh','Old Microreactor - massspec'])
    hosts.put(['rasppi28','Raspberry Pi','ssh','Parallel screening - Pressure readout'])
    hosts.put(['rasppi29','Raspberry Pi','ssh','Mobile gas wall - valve control'])
    hosts.put(['rasppi30','Raspberry Pi','ssh','MGW - temperature control'])
    hosts.put(['rasppi31','Raspberry Pi','ssh','STM 312 - sputter gun'])
    hosts.put(['rasppi33','Raspberry Pi','ssh','VHP-setup, valve-control'])
    hosts.put(['rasppi34','Raspberry Pi','ssh','Gas Alarm, 307'])
    hosts.put(['rasppi43','Raspberry Pi','ssh','VHP-setup, pressure and temperature'])
    hosts.put(['rasppi47','Raspberry Pi','ssh','Furnace Room, Temperature Control'])
    hosts.put(['rasppi49','Raspberry Pi','ssh','TOF emission control'])
    hosts.put(['rasppi51','Raspberry Pi','ssh','309, CVD chamber'])
    hosts.put(['rasppi53','Raspberry Pi','ssh','Mobile gas-wall multi purpose'])
    hosts.put(['rasppi54','Raspberry Pi','ssh','307, Muffle furnace'])
    hosts.put(['rasppi100','Raspberry Pi','ssh','Turbo controller, Microreactor'])
    hosts.put(['rasppi102','Raspberry Pi','ssh','Microreactors Pressure readout'])
    hosts.put(['microreactor','Windows','rdp','Main PC, Microreactor'])
    hosts.put(['microreactorng','Windows','None','Main PC, Microreactor NG'])
    hosts.put(['tofms','Windows','rdp','TOF-MS'])
    #hosts.put(['sputterchamber','Windows','rdp','Sputterchamber'])
    #hosts.put(['robertj','Fedora','http','Robert, office'])

    results = Queue.Queue()
    t = time.time()
    host_checkers = {}
    for i in range(0, 1):
        host_checkers[i] = CheckHost(hosts, results)
        host_checkers[i].start()
    hosts.join()

    sorted_results = {}
    while not results.empty():
        result = results.get()
        sorted_results[result[0]] = result

    status_string = ""
    for host in sorted_results.values():
        status_string += host[0] + ";"
        if host[1]:
            status_string += "1;"
            status_string += host[2] + ";"
            status_string += host[3] + ";"
        else:
            status_string += "0;;;"
        status_string += host[4] + ";"
        status_string += host[5]
        status_string += "\n"
    print(status_string)
