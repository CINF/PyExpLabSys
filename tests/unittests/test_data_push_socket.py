# -*- coding: utf-8 -*-
"""Unit tests for the DataPushSocket"""

import Queue
import time
import json
import ast
import threading
import SocketServer
# Allow for fast restart of a socket on a port for test purposes
SocketServer.UDPServer.allow_reuse_address = True
import pytest
from PyExpLabSys.common.sockets import DataPushSocket, CallBackThread
import PyExpLabSys.common.sockets
DATA = PyExpLabSys.common.sockets.DATA

#from PyExpLabSys.common.utilities import get_logger
#LOGGER = get_logger('Hallo', level='debug')


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
@pytest.fixture(params=['json', 'json_multiple_values'])
def json_data(request):
    """Return two different json data sets"""
    return DATA_SETS[request.param]


@pytest.fixture(params=['raw', 'raw_multiple_values'])
def raw_data(request):
    """Return two different raw data sets"""
    data_dict_name = request.param.replace('raw', 'json')
    return DATA_SETS[data_dict_name], DATA_SETS[request.param]


@pytest.yield_fixture
def dps(request):
    """DataPushSocket fixture, if requested in a class that has dps_kwargs
    class variable, use those in init
    """
    if hasattr(request, 'cls') and hasattr(request.cls, 'dps_kwargs'):
        dps = DataPushSocket(NAME, **request.cls.dps_kwargs)
    else:
        dps = DataPushSocket(NAME)
    dps.start()
    yield dps
    dps.stop()


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
def callback(request):
    """Generate a memory callback function and reset afterwards"""
    yield memory_callback
    global CALLBACK_MEMORY
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
    for n in range(argument['number']):
        out.append(argument[str(n)])
    return out


### Here starts the tests
def test_bad_init():
    """Test initializing with wrong parameters"""
    # Unknown action
    with pytest.raises(ValueError) as excinfo:
        DataPushSocket(NAME, action='oo')
    message = 'Unknown action \'oo\'. Must be one of: [\'store_last\', '\
        '\'enqueue\', \'callback_async\', \'callback_direct\']'
    assert(str(excinfo.value) == message)

    # Action 'callback' but supplied callback not call_able
    with pytest.raises(ValueError) as excinfo:
        DataPushSocket(NAME, action='callback_async',
                       callback='not callable str')
    message = 'Value for callback: \'not callable str\' is not callable'
    assert(str(excinfo.value) == message)

    # Action 'callback' but no supplied callback
    with pytest.raises(ValueError) as excinfo:
        DataPushSocket(NAME, action='callback_async')
    message = 'Value for callback: \'None\' is not callable'
    assert(str(excinfo.value) == message)

    # queue given but action not enqueue (deault action is store_last)
    with pytest.raises(ValueError) as excinfo:
        DataPushSocket(NAME, queue=Queue.Queue())
    message = 'The \'queue\' argument can only be used when the action is '\
        '\'enqueue\''
    assert(str(excinfo.value) == message)

    # callback given but action not callback (deault action is store_last)
    with pytest.raises(ValueError) as excinfo:
        DataPushSocket(NAME, callback=dir)
    message = 'The \'callback\' argument can only be used when the action is '\
        '\'callback_async\' or \'callback_direct\''
    assert(str(excinfo.value) == message)

    # Unknown return_format given
    with pytest.raises(ValueError) as excinfo:
        DataPushSocket(NAME, return_format='blah')
    message = 'The \'return_format\' argument may only be one of the '\
        '\'json\', \'raw\' or \'string\' values'
    assert(str(excinfo.value) == message)


class TestInit(object):
    """Class that wraps test of successful initialization"""

    def init_common_tests(self, dps, action):
        """Common init tests (called by other tests, not by pytest)"""
        # action
        assert(dps.action == action)
        assert(DATA[PORT]['action'] == dps.action)
        # port
        assert(dps.port == PORT)
        assert(isinstance(DATA.get(PORT), dict))
        # last
        assert(dps.last == (None, None))
        assert((DATA[PORT]['last_time'],
                DATA[PORT]['last']) == dps.last)
        # updated
        assert(dps.updated == (None, {}))
        assert((DATA[PORT]['updated_time'],
                DATA[PORT]['updated']) == dps.updated)
        # name
        assert(DATA[PORT]['name'] == NAME)
   
    def test_init_default(self, dps):
        """Test initialization with default patameters"""
        self.init_common_tests(dps, 'store_last')
        assert(dps.queue is None)
        assert(hasattr(DATA, 'queue') is False)

    def test_init_enqueue(self):
        """Test initialization with when action is enqueue"""
        dps = DataPushSocket(NAME, action='enqueue')
        dps.start()
        self.init_common_tests(dps, 'enqueue')
        assert(isinstance(dps.queue, Queue.Queue))
        assert(DATA[PORT]['queue'] is dps.queue)
        dps.stop()

    def test_init_custom_queue(self):
        """Test initialization when action is enqueue and use custom queue"""
        queue = Queue.Queue()
        dps = DataPushSocket(NAME, action='enqueue', queue=queue)
        dps.start()
        self.init_common_tests(dps, 'enqueue')
        assert(dps.queue is queue)
        assert(DATA[PORT]['queue'] is queue)
        dps.stop()

    def test_init_callback_async(self):
        """Test initialization when action is callback_async"""
        # Test init of callback
        dps = DataPushSocket(NAME, action='callback_async', callback=dir)
        dps.start()
        self.init_common_tests(dps, 'callback_async')
        assert(isinstance(dps.queue, Queue.Queue))
        assert(DATA[PORT]['queue'] is dps.queue)  
        assert(isinstance(dps._callback_thread, CallBackThread))
        assert(dps._callback_thread.callback is dir)
        dps.stop()

    def test_init_callback_direct_default(self):
        """Test initialization when action is callback_direct"""
        # Test init of callback
        dps = DataPushSocket(NAME, action='callback_direct', callback=dir)
        dps.start()
        self.init_common_tests(dps, 'callback_direct')
        assert(DATA[PORT]['callback'] is dir)
        assert(DATA[PORT]['return_format'] == 'json')
        dps.stop()


    def test_init_callback_direct_raw(self):
        """Test initialization when action is callback_direct"""
        # Test init of callback
        dps = DataPushSocket(NAME, action='callback_direct', callback=dir,
                             return_format='raw')
        dps.start()
        self.init_common_tests(dps, 'callback_direct')
        assert(DATA[PORT]['callback'] is dir)
        assert(DATA[PORT]['return_format'] == 'raw')
        dps.stop()


def test_unknown_command(dps, sock):
    """Test that we return unknown command"""
    expected = '{}#{}'.format(PyExpLabSys.common.sockets.PUSH_ERROR,
                              PyExpLabSys.common.sockets.UNKNOWN_COMMAND)
    # Nonsense command
    sock.sendto('bad bad command', (HOST, PORT))
    received = sock.recv(1024)
    assert(received == expected)

    # Bad command name
    sock.sendto('bad#nonsense', (HOST, PORT))
    received = sock.recv(1024)
    assert(received == expected)


def test_json_wn_bad_data(dps, sock):
    """Test the correct error handling for the json_wn command"""
    # Send string that cannot be parsed as JSON
    sock.sendto('json_wn#nonsense', (HOST, PORT))
    received = sock.recv(1024)
    message = '{}#The string \'nonsense\' could not be decoded as JSON'\
        .format(PyExpLabSys.common.sockets.PUSH_ERROR)
    assert(received == message)

    # Send string that can be parsed as JSON, but not into a dict
    sock.sendto('json_wn#"nonsense"', (HOST, PORT))
    received = sock.recv(1024)
    message = '{}#The object \'nonsense\' returned after decoding the JSON '\
        'string is not a dict'.format(PyExpLabSys.common.sockets.PUSH_ERROR)
    assert(received == message)


def test_raw_wn_bad_data(dps, sock):
    """Test the error handling for the raw_wn command"""
    # Test incorrect data part formatting, must be name:type:data i.e. 2 x ':'
    for string in ['bad', 'bad:bad', 'bad:bad:bad:bad']:
        command = 'raw_wn#{}'.format(string)
        sock.sendto(command, (HOST, PORT))
        received = sock.recv(1024)
        message = '{}#The data part \'{}\' did not match the expected format of '\
            '3 parts divided by \':\''.format(
                PyExpLabSys.common.sockets.PUSH_ERROR, string)
        assert(received == message)

    # Test unknown data type
    command = 'raw_wn#codename1:nondatatype:1'
    sock.sendto(command, (HOST, PORT))
    received = sock.recv(1024)
    message = '{}#The data type \'{}\' is unknown. Only {} are '\
        'allowed'.format(PyExpLabSys.common.sockets.PUSH_ERROR, 'nondatatype',
                         PyExpLabSys.common.sockets.TYPE_FROM_STRING.keys())
    assert(received == message)

    # Test conversion error
    command = 'raw_wn#codename1:int:hh'
    sock.sendto(command, (HOST, PORT))
    received = sock.recv(1024)
    message = '{}#Unable to convert values to \'int\'. Error is: invalid '\
        'literal for int() with base 10: \'hh\''.format(
            PyExpLabSys.common.sockets.PUSH_ERROR)
    assert(received == message)


def test_name(dps, sock):
    """Test the get name command"""
    command = 'name'
    sock.sendto(command, (HOST, PORT))
    received = sock.recv(1024)
    assert(received == '{}#{}'.format(PyExpLabSys.common.sockets.PUSH_RET,
                                      NAME))


class TestDataTransfer(object):
    """Test the data transfer functionality"""

    def reply_test(self, reply, data):
        """Perform test and comparisons on the reply"""
        response, data_back = reply.split('#')
        data_back = ast.literal_eval(data_back)
        assert(response == PyExpLabSys.common.sockets.PUSH_ACK)
        assert(data == data_back)    
    
    def last_test(self, data_push_socket, data, sent_time):
        """Test the last value"""
        received_time, received_data = data_push_socket.last
        assert(received_time - sent_time < 0.010)
        assert(data == received_data)    
    
    def updated_test(self, data_push_socket, data, sent_time):
        """Test the updated value"""
        received_time, received_data = data_push_socket.updated
        assert(received_time - sent_time < 0.010)
        assert(data == received_data)

    def test_json_wn(self, dps, sock, json_data):
        """Test sending data with the json_wn command"""
        data_updated = {}
        # Loop over data sets
        for data in json_data:
            data_updated.update(data)
            command = 'json_wn#{}'.format(json.dumps(data))
            time_sent = time.time()
            sock.sendto(command, (HOST, PORT))
            reply = sock.recv(1024)
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
            sock.sendto(command, (HOST, PORT))
            reply = sock.recv(1024)
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
        self.received = []
        local_data = []

        # Add 10 data points
        for data in data_sample['data']:
            command = 'json_wn#{}'.format(json.dumps(data))
            sock.sendto(command, (HOST, PORT))
            # Append data to local list with timestamp
            local_data.append((time.time(), data))
            reply = sock.recv(1024)
            # Check that the command was successful
            assert(reply.startswith(PyExpLabSys.common.sockets.PUSH_ACK))

        # Give the dps time to clear the queue by calling the callback
        time.sleep(0.1)
        # Check that the correct data is there and received in less than 10 ms
        for sent, received in zip(local_data, CALLBACK_MEMORY):
            assert(abs(received[0] - sent[0])  < 0.010)
            assert(sent[1] == received[1])

        # Check that queue has been emptied and that last and updated makes
        # sense
        assert(dps.queue.qsize() == 0)
        assert(dps.last[1] == data_sample['last'])
        assert(dps.last[0] - local_data[-1][0] < 0.010)
        assert(dps.updated[1] == data_sample['updated'])
        assert(dps.updated[0] - local_data[-1][0] < 0.010)


class TestCallBackReturnJson(object):
    """Test the callback functionality with json return"""
    # Used in dps fixture to init dps with certain kwargs.
    dps_kwargs = {'action': 'callback_direct',
                  'callback': echo_callback}

    def test_callback(self, dps, sock, data_sample):
        """Test the callback and test json return values"""
        for data in data_sample['data']:
            command = 'json_wn#{}'.format(json.dumps(data))
            reply = send_and_resc(sock, command)
            assert(reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#'))
            data_back = json.loads(reply.split('#')[1])
            assert(data == data_back)

    def test_none_return(self, dps, sock):
        """Test the return of a None value"""
        command = 'json_wn#{}'.format(json.dumps(DATA_SETS['NONE']))
        reply = send_and_resc(sock, command)
        assert(reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#'))
        data_back = json.loads(reply.split('#')[1])
        assert(data_back is None)


class TestCallBackReturnRaw(object):
    """Test the callback functionality with raw return"""
    # Used in dps fixture to init dps with certain kwargs.
    dps_kwargs = {'action': 'callback_direct', 'callback': echo_callback,
                  'return_format': 'raw'}

    def test_callback(self, dps, sock, data_sample):
        """Test the callback and test raw return values"""
        for data in data_sample['data']:
            command = 'json_wn#{}'.format(json.dumps(data))
            reply = send_and_resc(sock, command)
            assert(reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#'))
            data_back = reply.split('#')[1]
            expected = '{}:float:{}'.format(*data.items()[0])
            assert(data_back == expected)

    def test_callback_multiple_values(self, dps, sock):
        """Test the callback and test raw return values with multiple values"""
        data = {'myints': [42, 47]}
        command = 'json_wn#{}'.format(json.dumps(data))
        reply = send_and_resc(sock, command)
        assert(reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#'))
        data_back = reply.split('#')[1]
        expected = '{}:int:{},{}'.format(data.keys()[0], *data.values()[0])
        assert(data_back == expected)

    def test_none_return(self, dps, sock):
        """Test the return of a None value"""
        command = 'raw_wn#action:str:None'
        reply = send_and_resc(sock, command)
        assert(reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#'))
        data_back = reply.split('#')[1]
        assert(data_back == 'None')


class TestCallBackReturnRawList(object):
    """Test the callback functionality with raw return"""
    # Used in dps fixture to init dps with certain kwargs.
    dps_kwargs = {'action': 'callback_direct', 'callback': echo_list_callback,
                  'return_format': 'raw'}

    def test_callback_list_of_lists(self, dps, sock):
        """Test the callback and test raw return values with a list of lists"""
        data = {'number': 3, '0': [1.0, 42.0], '1': [1.5, 45.6],
                '2': [2.0, 47.0]}
        command = 'json_wn#{}'.format(json.dumps(data))
        reply = send_and_resc(sock, command)
        assert(reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#'))
        data_back = reply.split('#')[1]
        expected = 'float:1.0,42.0&1.5,45.6&2.0,47.0'
        assert(data_back == expected)


class TestCallBackReturnStr(object):
    """Test the callback functionality with string return"""
    # Used in dps fixture to init dps with certain kwargs.
    dps_kwargs = {'action': 'callback_direct', 'callback': echo_callback,
                  'return_format': 'string'}

    def test_callback(self, dps, sock, data_sample):
        """Test the callback and test str return values"""
        for data in data_sample['data']:
            command = 'json_wn#{}'.format(json.dumps(data))
            reply = send_and_resc(sock, command)
            assert(reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#'))
            data_back = reply.split('#')[1]
            expected = '{{u\'{}\': {}}}'.format(*data.items()[0])
            assert(data_back == expected)

    def test_none_return(self, dps, sock):
        """Test the return of a None value"""
        command = 'json_wn#{}'.format(json.dumps(DATA_SETS['NONE']))
        reply = send_and_resc(sock, command)
        assert(reply.startswith(PyExpLabSys.common.sockets.PUSH_RET + '#'))
        data_back = reply.split('#')[1]
        assert(data_back == 'None')


class TestEnqueue(object):
    """Test the enqueue functionality"""
    # Used in dps fixture to init dps with certain kwargs
    dps_kwargs = {'action': 'enqueue'}

    def test_enqueue(self, sock, data_sample, dps):
        """Test that data is enqueued (queue fixture returns both custom queue and
        None)
        """
        # Send data
        for data in data_sample['data']:
            command = 'json_wn#{}'.format(json.dumps(data))
            sock.sendto(command, (HOST, PORT))
            reply = sock.recv(1024)
            # Check that the command was successful
            assert(reply.startswith(PyExpLabSys.common.sockets.PUSH_ACK))
        # Check that it was received
        for data in data_sample['data']:
            data_received = dps.queue.get()
            assert(data == data_received)
        # Check that queue has been emptied and that last and updated makes
        # sense
        assert(dps.queue.qsize() == 0)
        assert(dps.last[1] == data_sample['last'])
        assert(dps.updated[1] == data_sample['updated'])

    def test_own_dequeuer(self, sock, data_sample, dps):
        """Test manual dequeuer (queue fixture returns both custom queue and None)
        """
        dequeuer = Dequeuer(dps.queue)
        # Send data
        local_data = []
        for data in data_sample['data']:
            command = 'json_wn#{}'.format(json.dumps(data))
            sock.sendto(command, (HOST, PORT))
            local_data.append((time.time(), data))
            reply = sock.recv(1024)
            # Check that the command was successful
            assert(reply.startswith(PyExpLabSys.common.sockets.PUSH_ACK))
        # Give the dps time to clear the queue
        time.sleep(0.1)
        dequeuer.stop = True
        time.sleep(0.1)
        # Check that the correct data is there and received in less than 10 ms
        for sent, received in zip(local_data, dequeuer.received):
            assert(abs(received[0] - sent[0])  < 0.010)
            assert(sent[1] == received[1])


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

    def run(self):
        """Pull item from the queue"""
        while not self.stop:
            try:
                item = self.queue.get(True, 0.1)
                self.received.append((time.time(), item))
            except Queue.Empty:
                pass
