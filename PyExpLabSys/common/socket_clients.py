"""This file implements Python clients for the DateDataPullSocket"""

from __future__ import unicode_literals, print_function


import socket
import sys
import json


OLD_DATA = 'OLD_DATA'
CHUNK_SIZE = 1024


class DateDataPullClient(object):
    """Client for the DateDataPullClient

    codenames and name are available as attributes
    """

    def __init__(self, host, expected_socket_name, port=9000, exception_on_old_data=True):
        """Initialize the DateDataPullClient object"""
        self.exception_on_old_data = exception_on_old_data
        self.socket_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host_port = (host, port)

        # Read name and test expected_socket_name
        self.name = self._communicate('name')
        if self.name != expected_socket_name:
            msg = 'The name of the socket at {} was not "{}" as expected, but "{}"'
            raise ValueError(msg.format(self.host_port, expected_socket_name, self.name))

        # Read codenames
        codenames_json = self._communicate('codenames_json')
        self.codenames = json.loads(codenames_json)
        self.codenames_set = set(self.codenames)
        

    def _communicate(self, command):
        """Encode, send and decode a command for a socket"""
        self.socket_.sendto(command.encode('utf-8'), self.host_port)
        # Received all
        received = b''
        while True:
            chunk = self.socket_.recv(CHUNK_SIZE)
            received += chunk
            if len(chunk) < CHUNK_SIZE:
                break
        return received.decode('utf-8')
    
    def get_field(self, fieldname):
        """Return field by name"""
        # Check for valud fieldname
        if fieldname not in self.codenames_set:
            msg = 'Unknown fieldnames, valid fields are: {}'.format(self.codenames)
            raise ValueError(msg)
    
        data_json = self._communicate('{}#json'.format(fieldname))
        data = json.loads(data_json)
        if data == OLD_DATA and self.exception_on_old_data:
            raise ValueError('Old data')
        return data

    def get_all_fields(self):
        """Return all fields"""
        data_json = self._communicate('json_wn')
        data = json.loads(data_json)
        for fieldname, value in data.items():
            if value == OLD_DATA and self.exception_on_old_data:
                raise ValueError('Old data, for field "{}"'.format(fieldname))
        return data

    def get_status(self):
        """Return the system status of the socket host"""
        status_json = self._communicate("status")
        return json.loads(status_json)

    def __getattr__(self, name):
        """Custom getattr to allow getting fields as attributes"""
        if name in self.codenames_set:
            return self.get_field(name)

        msg = "{} object has no attribute '{}'".format(self.__class__.__name__, name)
        raise AttributeError(msg)
        


def module_demo():
    date_data_pull_client = DateDataPullClient('127.0.0.1', 'testsocket')
    print("Name:", date_data_pull_client.name)
    print("Codenames:", date_data_pull_client.codenames)
    print("new:", date_data_pull_client.get_field('new'))
    try:
        print(date_data_pull_client.get_field('old'))
    except ValueError as exp:
        print('old raises', exp, 'as expected')
    try:
        date_data_pull_client.get_all_fields()
    except ValueError as exp:
        print('all raises', exp, 'as expected')

    date_data_pull_client.exception_on_old_data = False
    print("All:", date_data_pull_client.get_all_fields())

    print(date_data_pull_client.new)

    from pprint import pprint
    pprint(date_data_pull_client.get_status())


if __name__ == '__main__':
    module_demo()
