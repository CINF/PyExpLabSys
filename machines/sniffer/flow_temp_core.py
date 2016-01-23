# pylint: disable=invalid-name

"""This file contains the core set flow and and control temperature logic"""

from __future__ import print_function
from time import time, sleep
#from ubd.pyqt.threaded_methods import ThreadedMethod

from threading import Thread

import socket
import json

CODENAMES = ['21984878', '21984877', '21984876', '21984879']


class FlowTempCore(object):
    """Main flow and temperature control class"""

    def __init__(self, ui):
        """Initialize FlowTempCore"""
        self.ui = ui
        
        # Initialize flows
        self.flows = {}
        for codename in CODENAMES:
            self.flows[codename] = [time(), 0.0]
        
        # Setting up socket
        self.ip_port_get = ('rasppi37', 9000)
        self.ip_port_set = ('rasppi37', 8500)
        self.sock_get = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_set = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                
        # Start up flow reader thread
        self.flow_thread_reader = Thread(target = self.read_flows)
        self.flow_thread_reader.daemon = True
        self.stop_flow_thread_reader = False
        self.flow_thread_reader.start()
    
    def stop(self):
        """stop everything running"""
        self.stop_flow_thread_reader = True
        sleep(2)

    def set_flow(self, codename, value):
        """Send value for flow_name to control box"""
        print('### Send', value, 'to', codename)
        data = {codename: value}
        data_str = 'json_wn#' + json.dumps(data)
        data_bytes = data_str.encode('ascii')
        self.sock_set.sendto(data_bytes, self.ip_port_set)
        response, _ = self.sock_set.recvfrom(1024)
        print(response)
        if response.decode('ascii').startswith('ACK'):
            print('Great succes!')
        else:
            print('Damn it, time for beer!')
        print(data_bytes)

    #@ThreadedMethod
    def start_flow_file(self, filepath):
        """Start the flow file"""
        print('### Start flow file' + filepath)

    def stop_flow_file(self):
        """Stop running the active flow file"""
        print('### Stop flow file')
        
    def read_flows(self):
        """Reading flows"""
        while not self.stop_flow_thread_reader:
            self.sock_get.sendto(b'json_wn', self.ip_port_get)
            raw_data, _ = self.sock_get.recvfrom(1024)
            data = json.loads(raw_data.decode('ascii'))
            for codename in CODENAMES:
                self.flows[codename] = data[codename]
            #print('current flows', self.flows)
            sleep(1)
        print('no longer reading flows')

    def get_flows(self):
        """Return the current flows"""
        return dict(self.flows)


if __name__ == '__main__':
    raise RuntimeError("Run main.py instead")
