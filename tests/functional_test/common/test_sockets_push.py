# -*- coding: utf-8 -*-
# pylint: disable = no-member,star-args,protected-access,too-few-public-methods
# pylint: disable = unused-argument,redefined-outer-name,no-self-use,import-error

# NOTE: About pylint disable. Everything on the second line are
# disables that simply makes no sense when using pytest and fixtures

"""Unit tests for the DataPushSocket"""

from __future__ import unicode_literals

import sys
try:
    import Queue
except ImportError:
    import queue as Queue
import time
import json
import ast
import threading
import socket
try:
    import SocketServer
except ImportError:
    import socketserver as SocketServer
# Allow for fast restart of a socket on a port for test purposes
SocketServer.UDPServer.allow_reuse_address = True
import pytest
from PyExpLabSys.common.sockets import DataPushSocket
import PyExpLabSys.common.sockets
DATA = PyExpLabSys.common.sockets.DATA
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


### Module variables
HOST = "localhost"
PORT = 8500
NAME = 'Driver push socket for giant laser on the moon'
CALLBACK_MEMORY = []

### Define data sets
DATA_SETS = {}
DATA_SETS['json'] = [
    {'name1': 47, 'name2': 47.0, 'name3': 'Live long and prosper',
     'name4': False},
    {'name1': 42, 'name2': 42.0},
    {'name3': 'Today is a good day to die', 'name4': False}
]
DATA_SETS['raw'] = [
    'raw_wn#name1:int:47;name2:float:47.0;name3:str:Live long and prosper;'\
        'name4:bool:False',
    'raw_wn#name1:int:42;name2:float:42.0',
    'raw_wn#name3:str:Today is a good day to die;name4:bool:False'
]
# Multiple values test data sets
DATA_SETS['json_multiple_values'] = [
    {'name1': [47, 42], 'name2': False},
    {'name2': [42.0, 47.0]}
]
DATA_SETS['raw_multiple_values'] = [
    'raw_wn#name1:int:47,42;name2:bool:False',
    'raw_wn#name2:float:42.0,47.0'
]
# Data sets to make the call back return None or not return (the same)
DATA_SETS['NONE'] = {'action': 'None'}


### Define fixtures
@pytest.yield_fixture
def sock():
    """Client socket fixture"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    yield sock
    sock.close()


@pytest.fixture(params=['json', 'json_multiple_values'])
def json_data(request):
    """Return two different json data sets"""
    return DATA_SETS[request.param]


@pytest.fixture(params=['raw', 'raw_multiple_values'])
def raw_data(request):
    """Return two different raw data sets"""
    data_dict_name = request.param.replace('raw', 'json')
    return DATA_SETS[data_dict_name], DATA_SETS[request.param]


@pytest.yield_fixture(scope='class')
def class_dps(request):
    """DataPushSocket fixture

    If requested in a class that has dps_kwargs class variable, use those in init

    .. note:: This fixture lasts for the duration of a test class. It has been setup like this
       because the sockets take a long time to shut down. So in order to save time on the test
       run, we only initiate the socket once per class, but reset it in the dps fixture. It is
       the dps fixture that should be used.

    """
    if hasattr(request, 'cls') and hasattr(request.cls, 'dps_kwargs'):
        dps_ = DataPushSocket(NAME, **request.cls.dps_kwargs)
    else:
        dps_ = DataPushSocket(NAME)
    dps_.start()
    yield dps_
    dps_.stop()


@pytest.fixture(scope='function')
def dps(class_dps):
    """DataPushSocket fixture

    If requested in a class that has dps_kwargs class variable, use those in init (via the
    class_dps fixture).

    .. note:: This fixture takes an DataPushSocket (dps) instance as an argument, which is
       re-used throughout the entire test class. This fixture, which only has the scope of
       a function, will then reset the socket before every method.
    """
    class_dps.clear_updated()
    class_dps.set_last_to_none()
    return class_dps


@pytest.fixture(params=['new_name', 'same_name'])
def data_sample(request):
    """Generate test data, params determine whether to use different names"""
    out = {'data': [], 'updated': {}}
    for number in range(10):
        if request.param == 'new_name':
            data = {'name{}'.format(number): float(number)}
        else:
            data = {'sanename': float(number)}
        out['data'].append(data)
        out['last'] = data
        out['updated'].update(data)
    return out


@pytest.fixture(params=['built_in_queue', 'custom_queue'])
def queue(request):
    """Generate the queue parameter, either None or Queue.Queue()"""
    if request.param == 'custom_queue':
        return Queue.Queue()


@pytest.yield_fixture
def callback(request):  # pylint: disable=unused-argument
    """Generate a memory callback function and reset afterwards"""
    yield memory_callback
    global CALLBACK_MEMORY  # pylint: disable=global-statement
    CALLBACK_MEMORY = []


### Helper functions
def send_and_resc(sock, command):
    """Helper UPD socket send and receive"""
    sock.sendto(command, (HOST, PORT))
    data, _ = sock.recvfrom(1024)
    return data


def memory_callback(argument):
    """A callback function with memory, remember to clear it"""
    CALLBACK_MEMORY.append(argument)


def memory_callback_with_time(argument):
    """Memory callback with time prefix"""
    memory_callback((time.time(), argument))


def echo_callback(argument):
    """Echo callback function"""
    if argument.get('action') != 'None':
        return argument


def echo_list_callback(argument):
    """Echo callback function which sends a list back

    Turns {'number': 3, '0': [1.0, 42.0], '1': [1.5, 45.6], '2': [2.0, 47.0]}
    into [[1.0, 42.0], [1.5, 45.6], [2.0, 47.0]]
    """
    out = []
    for number in range(argument['number']):
        out.append(argument[str(number)])
    return out


### Here starts the tests
class TestErrors(object):
    """Simple tests of errors"""

    def test_unknown_command(self, dps, sock):
        """Test that we return unknown command"""
        expected = '{}#{}'.format(PyExpLabSys.common.sockets.PUSH_ERROR,
                                  PyExpLabSys.common.sockets.UNKNOWN_COMMAND).encode('ascii')
        # Nonsense command
        sock.sendto(b'bad bad command', (HOST, PORT))
        received = sock.recv(1024)
        assert received == expected

        # Bad command name
        sock.sendto(b'bad#nonsense', (HOST, PORT))
        received = sock.recv(1024)
        assert received == expected


    def test_json_wn_bad_data(self, dps, sock):
        """Test the correct error handling for the json_wn command"""
        # Send string that cannot be parsed as JSON
        sock.sendto(b'json_wn#nonsense', (HOST, PORT))
        received = sock.recv(1024)
        message = '{}#The string \'nonsense\' could not be decoded as JSON'\
            .format(PyExpLabSys.common.sockets.PUSH_ERROR)
        assert received == message.encode('ascii')

        # Send string that can be parsed as JSON, but not into a dict
        sock.sendto(b'json_wn#"nonsense"', (HOST, PORT))
        received = sock.recv(1024)
        message = '{}#The object \'nonsense\' returned after decoding the JSON '\
            'string is not a dict'.format(PyExpLabSys.common.sockets.PUSH_ERROR)
        assert received == message.encode('ascii')


    def test_raw_wn_bad_data(self, dps, sock):
        """Test the error handling for the raw_wn command"""
        # Test incorrect data part formatting, must be name:type:data i.e. 2 x ':'
        for string in ['bad', 'bad:bad', 'bad:bad:bad:bad']:
            command = 'raw_wn#{}'.format(string).encode('ascii')
            sock.sendto(command, (HOST, PORT))
            received = sock.recv(1024)
            message = '{}#The data part \'{}\' did not match the expected '\
                      'format of 3 parts divided by \':\''.format(
                    PyExpLabSys.common.sockets.PUSH_ERROR, string)
            assert received == message.encode('ascii')

        # Test unknown data type
        command = b'raw_wn#codename1:nondatatype:1'
        sock.sendto(command, (HOST, PORT))
        received = sock.recv(1024)
        message = '{}#The data type \'{}\' is unknown. Only {} are '\
            'allowed'.format(PyExpLabSys.common.sockets.PUSH_ERROR, 'nondatatype',
                             PyExpLabSys.common.sockets.TYPE_FROM_STRING.keys())
        assert received == message.encode('ascii')

        # Test conversion error
        command = b'raw_wn#codename1:int:hh'
        sock.sendto(command, (HOST, PORT))
        received = sock.recv(1024)
        message = '{}#Unable to convert values to \'int\'. Error is: invalid '\
            'literal for int() with base 10: \'hh\''.format(
                PyExpLabSys.common.sockets.PUSH_ERROR)
        assert received == message.encode('ascii')


    def test_name(self, dps, sock):
        """Test the get name command"""
        sock.sendto(b'name', (HOST, PORT))
        received = sock.recv(1024)
        assert received == \
            '{}#{}'.format(PyExpLabSys.common.sockets.PUSH_RET, NAME).encode('ascii')


class TestDataTransfer(object):
    """Test the data transfer functionality"""

    @staticmethod
    def reply_test(reply, data):
        """Perform test and comparisons on the reply

        reply and data are unicode object
        """
        response, data_back = reply.split('#')
        data_back = ast.literal_eval(data_back)
        assert response == PyExpLabSys.common.sockets.PUSH_ACK
        assert data == data_back

    @staticmethod
    def last_test(data_push_socket, data, sent_time):
        """Test the last value"""
        received_time, received_data = data_push_socket.last
        assert received_time - sent_time < 0.010
        assert data == received_data

    @staticmethod
    def updated_test(data_push_socket, data, sent_time):
        """Test the updated value"""
        received_time, received_data = data_push_socket.updated
        assert received_time - sent_time < 0.010
        assert data == received_data

    def test_json_wn(self, dps, sock, json_data):
        """Test sending data with the json_wn command"""
        data_updated = {}
        # Loop over data sets
        for data in json_data:
            data_updated.update(data)
            command = 'json_wn#{}'.format(json.dumps(data)).encode('ascii')
            time_sent = time.time()
            sock.sendto(command, (HOST, PORT))
            reply = sock.recv(1024).decode('ascii')
            # Test the reply, last and updated value and times of reception
            self.reply_test(reply, data)
            self.last_test(dps, data, time_sent)
            self.updated_test(dps, data_updated, time_sent)

    def test_raw_wn(self, dps, sock, raw_data):
        """Test sending data with the raw_wn (with names) command"""
        data_updated = {}
        # Loop over data sets
        for data, command in zip(*raw_data):
            data_updated.update(data)
            time_sent = time.time()
            sock.sendto(command.encode('ascii'), (HOST, PORT))
            reply = sock.recv(1024).decode('ascii')
            # Test the reply, last and updated value and times of reception
            self.reply_test(reply, data)
            self.last_test(dps, data, time_sent)
            self.updated_test(dps, data_updated, time_sent)


class TestCallBack(object):
    """Test the call back functionality"""

    # Used in dps fixture to init dps with certain kwargs.
    # NOTE. The fixture callback_with memory cannot be used here, so the
    # ordinary memory_callback_with_time function is used and then it is
    # ensured to be reset by passing the callback fixture to the testfunctions
    # even if they aren't being used
    dps_kwargs = {'action': 'callback_async',
                  'callback': memory_callback_with_time}

    def test_callback(self, dps, sock, data_sample, callback):
        """Test the call back functionality. """
        # Init the sent and received list of time stamps and data
        self.received = []  # pylint: disable=attribute-defined-outside-init
        local_data = []

        # Add 10 data points
        for data in data_sample['data']:
            command = 'json_wn#{}'.format(json.dumps(data)).encode('ascii')
            sock.sendto(command, (HOST, PORT))
            # Append data to local list with timestamp
            local_data.append((time.time(), data))
            reply = sock.recv(1024).decode('ascii')
            # Check that the command was successful
            assert reply.startswith(PyExpLabSys.common.sockets.PUSH_ACK)

        # Give the dps time to clear the queue by calling the callback
        while dps.queue.qsize() > 0:
            time.sleep(1E-4)

        # Check that the correct data is there and received in less than 10 ms
        for sent, received in zip(local_data, CALLBACK_MEMORY):
            assert abs(received[0] - sent[0]) < 0.020
            assert sent[1] == received[1]

        # Check that queue has been emptied and that last and updated makes
        # sense
        assert dps.queue.qsize() == 0
        assert dps.last[1] == data_sample['last']
        assert dps.last[0] - local_data[-1][0] < 0.010
        assert dps.updated[1] == data_sample['updated']
        assert dps.updated[0] - local_data[-1][0] < 0.010


class TestCallBackReturnJson(object):
    """Test the callback functionality with json return"""
    # Used in dps fixture to init dps with certain kwargs.
    dps_kwargs = {'action': 'callback_direct',
                  'callback': echo_callback}

    def test_callback(self, dps, sock, data_sample):
        """Test the callback and test json return values"""
        for data in data_sample['data']:
            command = 'json_wn#{}'.format(json.dumps(data)).encode('ascii')
            reply = send_and_resc(sock, command).decode('ascii')
            assert reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#')
            data_back = json.loads(reply.split('#')[1])
            assert data == data_back

    def test_none_return(self, dps, sock):
        """Test the return of a None value"""
        command = 'json_wn#{}'.format(json.dumps(DATA_SETS['NONE'])).encode('ascii')
        reply = send_and_resc(sock, command).decode('ascii')
        assert reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#')
        data_back = json.loads(reply.split('#')[1])
        assert data_back is None


class TestCallBackReturnRaw(object):
    """Test the callback functionality with raw return"""
    # Used in dps fixture to init dps with certain kwargs.
    dps_kwargs = {'action': 'callback_direct', 'callback': echo_callback,
                  'return_format': 'raw'}

    def test_callback(self, dps, sock, data_sample):
        """Test the callback and test raw return values"""
        for data in data_sample['data']:
            command = 'json_wn#{}'.format(json.dumps(data)).encode('ascii')
            reply = send_and_resc(sock, command).decode('ascii')
            assert reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#')
            data_back = reply.split('#')[1]
            expected = '{}:float:{}'.format(*list(data.items())[0])
            assert data_back == expected

    def test_callback_multiple_values(self, dps, sock):
        """Test the callback and test raw return values with multiple values"""
        data = {'myints': [42, 47]}
        command = 'json_wn#{}'.format(json.dumps(data)).encode('ascii')
        reply = send_and_resc(sock, command).decode('ascii')
        assert reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#')
        data_back = reply.split('#')[1]
        expected = '{}:int:{},{}'.format(list(data.keys())[0], *list(data.values())[0])
        assert data_back == expected

    def test_none_return(self, dps, sock):
        """Test the return of a None value"""
        command = b'raw_wn#action:str:None'
        reply = send_and_resc(sock, command).decode('ascii')
        assert reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#')
        data_back = reply.split('#')[1]
        assert data_back == 'None'


class TestCallBackReturnRawList(object):
    """Test the callback functionality with raw return"""
    # Used in dps fixture to init dps with certain kwargs.
    dps_kwargs = {'action': 'callback_direct', 'callback': echo_list_callback,
                  'return_format': 'raw'}

    def test_callback_list_of_lists(self, dps, sock):
        """Test the callback and test raw return values with a list of lists"""
        data = {'number': 3, '0': [1.0, 42.0], '1': [1.5, 45.6],
                '2': [2.0, 47.0]}
        command = 'json_wn#{}'.format(json.dumps(data)).encode('ascii')
        reply = send_and_resc(sock, command).decode('ascii')
        assert reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#')
        data_back = reply.split('#')[1]
        expected = 'float:1.0,42.0&1.5,45.6&2.0,47.0'
        assert data_back == expected


class TestCallBackReturnStr(object):
    """Test the callback functionality with string return"""
    # Used in dps fixture to init dps with certain kwargs.
    dps_kwargs = {'action': 'callback_direct', 'callback': echo_callback,
                  'return_format': 'string'}

    def test_callback(self, dps, sock, data_sample):
        """Test the callback and test str return values"""
        for data in data_sample['data']:
            command = 'json_wn#{}'.format(json.dumps(data)).encode('ascii')
            reply = send_and_resc(sock, command).decode('ascii')
            assert reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#')
            data_back = reply.split('#')[1]
            if sys.version_info[0] == 3:
                expected = '{{\'{}\': {}}}'.format(*list(data.items())[0])
            else:
                expected = '{{u\'{}\': {}}}'.format(*list(data.items())[0])
            assert data_back == expected

    def test_none_return(self, dps, sock):
        """Test the return of a None value"""
        command = 'json_wn#{}'.format(json.dumps(DATA_SETS['NONE'])).encode('ascii')
        reply = send_and_resc(sock, command).decode('ascii')
        assert reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#')
        data_back = reply.split('#')[1]
        assert data_back == 'None'


class TestEnqueue(object):
    """Test the enqueue functionality"""
    # Used in dps fixture to init dps with certain kwargs
    dps_kwargs = {'action': 'enqueue'}

    def test_enqueue(self, sock, data_sample, dps):
        """Test that data is enqueued (queue fixture returns both custom queue
        and None)

        """
        # Send data
        for data in data_sample['data']:
            command = 'json_wn#{}'.format(json.dumps(data)).encode('ascii')
            sock.sendto(command, (HOST, PORT))
            reply = sock.recv(1024).decode('ascii')
            # Check that the command was successful
            assert reply.startswith(PyExpLabSys.common.sockets.PUSH_ACK)
        # Check that it was received
        for data in data_sample['data']:
            data_received = dps.queue.get()
            assert data == data_received
        # Check that queue has been emptied and that last and updated makes
        # sense
        assert dps.queue.qsize() == 0
        assert dps.last[1] == data_sample['last']
        assert dps.updated[1] == data_sample['updated']

    def test_own_dequeuer(self, sock, data_sample, dps):
        """Test manual dequeuer (queue fixture returns both custom queue and
        None)

        """
        dequeuer = Dequeuer(dps.queue)
        dequeuer.start()
        # Send data
        local_data = []
        for data in data_sample['data']:
            command = 'json_wn#{}'.format(json.dumps(data)).encode('ascii')
            sock.sendto(command, (HOST, PORT))
            local_data.append((time.time(), data))
            reply = sock.recv(1024).decode('ascii')
            # Check that the command was successful
            assert reply.startswith(PyExpLabSys.common.sockets.PUSH_ACK)

        # Give the dps time to clear the queue
        while dps.queue.qsize() > 0:
            time.sleep(1E-4)
        time.sleep(0.1)

        dequeuer.stop = True
        while dequeuer.isAlive():
            time.sleep(0.01)

        # Check that the correct data is there and received in less than 10 ms
        for sent, received in zip(local_data, dequeuer.received):
            assert abs(received[0] - sent[0]) < 0.010
            assert sent[1] == received[1]


class TestEnqueueCustomQueue(TestEnqueue):
    """Test the enqueue functionality with a custom queue. Inherits test
    functions from TestEnqueue
    """
    # Overwrite parent, Used in dps fixture to init dps with certain kwargs
    dps_kwargs = {'action': 'enqueue', 'queue': Queue.Queue()}


class Dequeuer(threading.Thread):
    """Class that minics locally pulling items from the queue"""

    def __init__(self, queue):
        super(Dequeuer, self).__init__()
        self.received = []
        self.stop = False
        self.queue = queue

    def run(self):
        """Pull item from the queue"""
        while not self.stop:
            try:
                item = self.queue.get(True, 0.1)
                self.received.append((time.time(), item))
            except Queue.Empty:
                pass
