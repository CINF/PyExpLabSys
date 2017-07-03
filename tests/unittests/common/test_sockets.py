# pylint: disable=too-many-lines,no-member,no-name-in-module,redefined-outer-name,
# pylint: disable=unused-argument,no-self-use,protected-access

"""This file contains unit tests for PyExpLabSys.common.sockets"""

from __future__ import unicode_literals, print_function

import sys
import time
import mock
import json
import collections
import socket
import pytest
from numpy import isclose
from PyExpLabSys.common import sockets
from PyExpLabSys.common.sockets import (
    bool_translate, socket_server_status, PullUDPHandler, CommonDataPullSocket, DataPullSocket,
    DateDataPullSocket, PushUDPHandler, DataPushSocket, CallBackThread
)
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

### Test data
if sys.version_info[0] == 3:
    QUEUE_CLASS_PATH = 'queue.Queue'
else:
    QUEUE_CLASS_PATH = 'Queue.Queue'
SERVER_ADDRESS = '42.42.42.42'
CLIENT_ADDRESS = '47.47.47.47'
PORT = 9876
NAME = 'my name'
SOCKET_NAME = 'my_socket'
FIRTS_MEASUREMENT_NAME = 'my_measurement'
SECOND_MEASUREMENT_NAME = 'my_measurement2'
CODENAMES = [FIRTS_MEASUREMENT_NAME, SECOND_MEASUREMENT_NAME]
SINGLE_DATA = {PORT: {'data': {FIRTS_MEASUREMENT_NAME: (42.0, 47.0)}}}
ALL_DATA = {PORT: {
    'data': {
        FIRTS_MEASUREMENT_NAME: (42.0, 47.0),
        SECOND_MEASUREMENT_NAME: (17.0, 1.0),
    },
    'name': NAME,
    'codenames': [FIRTS_MEASUREMENT_NAME, SECOND_MEASUREMENT_NAME],
}}
SOCKETS_PATH = 'PyExpLabSys.common.sockets.{}'
ANY_RETURN = 'any_return_value'


### Fixtures
@pytest.fixture
def mocket():
    """A socket fixture"""
    return mock.MagicMock()


@pytest.yield_fixture
def sockets_data_single():
    """A fixture for replaced sockets.DATA with SINGLE_DATA"""
    old_data = sockets.DATA
    sockets.DATA = SINGLE_DATA
    yield sockets.DATA
    sockets.DATA = old_data


@pytest.yield_fixture
def sockets_data_all():
    """A fixture for replaced sockets.DATA with ALL_DATA"""
    old_data = sockets.DATA
    sockets.DATA = ALL_DATA
    yield sockets.DATA
    sockets.DATA = old_data


@pytest.fixture
def server():
    """A server fixture"""
    server_ = mock.MagicMock()
    server_.server_address = [SERVER_ADDRESS, PORT]
    return server_


@pytest.yield_fixture
def pull_udp_handler(mocket, server):
    """A PullUDPHandler fixture"""
    # Since init on a handler calls handle, mock it out while initing, so that it can be tested
    # separately
    with mock.patch('PyExpLabSys.common.sockets.PullUDPHandler.handle'):
        udp_handler = PullUDPHandler(('dummy_request', mocket), CLIENT_ADDRESS, server)
        udp_handler.port = PORT
        yield udp_handler


@pytest.fixture(scope='function')
def cdps_init_args():
    """A fixture with init args for CommonDataPullSocket"""
    return {
        'name': NAME, 'codenames': list(CODENAMES), 'port': PORT,
        'default_x': 5.0, 'default_y': 3.0, 'timeouts': 1.0,
        'check_activity': True, 'activity_timeout': 10.0,
        'handler_class': sockets.PullUDPHandler
    }


@pytest.yield_fixture
def udp_server():
    """A UDPServer fixure"""
    if sys.version_info[0] == 2:
        with mock.patch('SocketServer.UDPServer') as udp_server:
            yield udp_server
    # SocketServer was renamed to socketserver in Python 3
    else:
        with mock.patch('socketserver.UDPServer') as udp_server:
            yield udp_server

@pytest.yield_fixture
def clean_data():
    """A clean sockets.DATA fixture"""
    old_data = sockets.DATA
    sockets.DATA = {}
    yield sockets.DATA
    sockets.DATA = old_data


@pytest.yield_fixture
def push_udp_handler(mocket, server):
    """An any request PushUDPHandler"""
    # mock handle, which is called at instantiate time, inside a try except
    with mock.patch(SOCKETS_PATH.format('PushUDPHandler.handle')):
        yield PushUDPHandler(('any_request', mocket), CLIENT_ADDRESS, server)


### Tests
def test_bool_translate():
    """Test the bool_translate function"""
    assert bool_translate('True') is True
    assert bool_translate('False') is False
    for non_valid in ['false', 'true', '', '#&%/(']:
        with pytest.raises(ValueError):
            bool_translate(non_valid)


def test_socket_server_status():
    """Test the socket_server_status function"""
    # Save the current value of DATA
    old_data = sockets.DATA

    # Test standard value and no activity check
    activity = {'check_activity': False}
    sockets.DATA = {
        9876: {
            'name': 'Random name',
            'type': 'Some type',
            'activity': activity,
           }
    }
    status = socket_server_status()
    assert status[9876]['name'] == 'Random name'
    assert status[9876]['type'] == 'Some type'
    assert status[9876]['status'] == 'DISABLED'
    assert status[9876]['since_last_activity'] == None

    # Test ok activity check
    activity.update({
        'check_activity': True,
        'activity_timeout': 47.0,
        'last_activity': time.time() - 42.0,
    })
    status = socket_server_status()
    assert status[9876]['status'] == 'OK'
    assert isclose(status[9876]['since_last_activity'], 42.0, atol=0.1)

    # Test failed activity check
    activity.update({
        'activity_timeout': 42.0,
        'last_activity': time.time() - 47.0,
    })
    status = socket_server_status()
    assert status[9876]['status'] == 'INACTIVE'

    # Clean up DATA
    sockets.DATA = old_data


class TestPullUDPHandler(object):
    """Test the PullUDPHandler"""

    def test_handle_single_val_and_port(self, mocket, server):
        """Test the handle method single value case"""
        request = b'dummy#request'
        mock_return_value = 'mock return value'

        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler.handle')):
            handler = PullUDPHandler((request, mocket), CLIENT_ADDRESS, server)

        # Test single value case
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._single_value')) as _single_value:
            _single_value.return_value = mock_return_value
            with mock.patch(SOCKETS_PATH.format('PullUDPHandler._all_values')) as _all_values:
                handler.handle()
                _single_value.assert_called_once_with(request.decode('ascii'))
                assert not _all_values.called
                mocket.sendto.assert_called_once_with(mock_return_value.encode('ascii'),
                                                      CLIENT_ADDRESS)

        assert handler.port == PORT

    def test_handle_all_value(self, mocket, server):
        """Test the handle method all values case"""
        request = b'dummy_request'
        mock_return_value = 'mock return value'

        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler.handle')):
            handler = PullUDPHandler((request, mocket), CLIENT_ADDRESS, server)

        # Test all values case
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._single_value')) as _single_value:
            with mock.patch(SOCKETS_PATH.format('PullUDPHandler._all_values')) as _all_values:
                _all_values.return_value = mock_return_value
                handler.handle()
                _all_values.assert_called_once_with(request.decode('ascii'))
                assert not _single_value.called
                mocket.sendto.assert_called_once_with(mock_return_value.encode('ascii'),
                                                      CLIENT_ADDRESS)

    def test_single_raw(self, pull_udp_handler, sockets_data_single):
        """Test the _single_value raw case"""
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._old_data')) as _old_data:
            _old_data.return_value = False
            assert pull_udp_handler._single_value(FIRTS_MEASUREMENT_NAME + '#raw')\
                == '42.0,47.0'
            _old_data.assert_called_once_with(FIRTS_MEASUREMENT_NAME)

    def test_single_json(self, pull_udp_handler, sockets_data_single):
        """Test the _single_value json case"""
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._old_data')) as _old_data:
            _old_data.return_value = False
            assert pull_udp_handler._single_value(FIRTS_MEASUREMENT_NAME + '#json')\
                == '[42.0, 47.0]'
            _old_data.assert_called_once_with(FIRTS_MEASUREMENT_NAME)

    def test_single_old(self, pull_udp_handler, sockets_data_single):
        """Test the _single_value old data case"""
        # raw case
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._old_data')) as _old_data:
            _old_data.return_value = True
            assert pull_udp_handler._single_value(FIRTS_MEASUREMENT_NAME + '#raw')\
                == 'OLD_DATA'
            _old_data.assert_called_once_with(FIRTS_MEASUREMENT_NAME)

        # json case
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._old_data')) as _old_data:
            _old_data.return_value = True
            assert pull_udp_handler._single_value(FIRTS_MEASUREMENT_NAME + '#json')\
                == '"OLD_DATA"'
            _old_data.assert_called_once_with(FIRTS_MEASUREMENT_NAME)

    def test_single_unknown_command(self, pull_udp_handler, sockets_data_single):
        """Test the _single_value unknown command case"""
        assert pull_udp_handler._single_value(FIRTS_MEASUREMENT_NAME + '#nonsense')\
                == sockets.UNKNOWN_COMMAND

    def test_all_raw(self, pull_udp_handler, sockets_data_all):
        """Test the _all_values raw case"""
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._old_data')) as _old_data:
            _old_data.return_value = False
            assert pull_udp_handler._all_values('raw')\
                == '42.0,47.0;17.0,1.0'
            calls = [mock.call(FIRTS_MEASUREMENT_NAME), mock.call(SECOND_MEASUREMENT_NAME)]
            _old_data.assert_has_calls(calls)

    def test_all_json(self, pull_udp_handler, sockets_data_all):
        """Test the _all_values json case"""
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._old_data')) as _old_data:
            _old_data.return_value = False
            assert pull_udp_handler._all_values('json')\
                == '[[42.0, 47.0], [17.0, 1.0]]'
            calls = [mock.call(FIRTS_MEASUREMENT_NAME), mock.call(SECOND_MEASUREMENT_NAME)]
            _old_data.assert_has_calls(calls)

    def test_all_raw_with_names(self, pull_udp_handler, sockets_data_all):
        """Test the all values raw with names case"""
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._old_data')) as _old_data:
            _old_data.return_value = False
            expected = '{}:42.0,47.0;{}:17.0,1.0'.format(FIRTS_MEASUREMENT_NAME,
                                                         SECOND_MEASUREMENT_NAME)
            assert pull_udp_handler._all_values('raw_wn') == expected
            calls = [mock.call(FIRTS_MEASUREMENT_NAME), mock.call(SECOND_MEASUREMENT_NAME)]
            _old_data.assert_has_calls(calls)

    def test_all_json_with_names(self, pull_udp_handler, sockets_data_all):
        """Test the all values json with names case"""
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._old_data')) as _old_data:
            _old_data.return_value = False
            expected = {
                FIRTS_MEASUREMENT_NAME: [42.0, 47.0],
                SECOND_MEASUREMENT_NAME: [17.0, 1.0],
            }
            assert json.loads(pull_udp_handler._all_values('json_wn')) == expected
            calls = [mock.call(FIRTS_MEASUREMENT_NAME), mock.call(SECOND_MEASUREMENT_NAME)]
            _old_data.assert_has_calls(calls)

    def test_all_codenames_raw(self, pull_udp_handler, sockets_data_all):
        """Test the _all_values codenames raw case"""
        expected = FIRTS_MEASUREMENT_NAME + ',' + SECOND_MEASUREMENT_NAME
        assert pull_udp_handler._all_values('codenames_raw') == expected

    def test_all_codenames_json(self, pull_udp_handler, sockets_data_all):
        """Test the _all_values codenames json case"""
        expected = [FIRTS_MEASUREMENT_NAME, SECOND_MEASUREMENT_NAME]
        assert json.loads(pull_udp_handler._all_values('codenames_json')) == expected

    def test_all_name(self, pull_udp_handler, sockets_data_all):
        """Test the _all_values name case"""
        assert pull_udp_handler._all_values('name') == NAME

    def test_all_status(self, pull_udp_handler, sockets_data_all):
        """Test the _all_values name case"""
        # Set up mocks for SYSTEM_STATUS and socket_server_status
        with mock.patch('PyExpLabSys.common.sockets.SYSTEM_STATUS') as system_status:
            system_status.complete_status.return_value = 1
            with mock.patch('PyExpLabSys.common.sockets.socket_server_status') as\
                 socket_server_status:
                socket_server_status.return_value = 2

                # Test the expected output
                expected = {'system_status': 1, 'socket_server_status': 2}
                assert json.loads(pull_udp_handler._all_values('status')) == expected

    def test_all_invalid_command(self, pull_udp_handler):
        """Test the all invalid command case"""
        assert pull_udp_handler._all_values('invalid_command') == sockets.UNKNOWN_COMMAND

    def test_old_data_with_date_data(self, pull_udp_handler, sockets_data_single):
        """Test the _old_date date data true case"""
        sockets_data_single[PORT]['type'] = 'date'

        # Test without a timeout
        sockets_data_single[PORT]['timeouts'] = {}
        assert pull_udp_handler._old_data(FIRTS_MEASUREMENT_NAME) is False

        # Test with timeout and old data
        sockets_data_single[PORT]['timeouts'] = {FIRTS_MEASUREMENT_NAME: 1.0}
        sockets_data_single[PORT]['data'][FIRTS_MEASUREMENT_NAME] = (time.time() - 2.0, 47)
        assert pull_udp_handler._old_data(FIRTS_MEASUREMENT_NAME) is True

        # Test with timeout and new data
        sockets_data_single[PORT]['data'][FIRTS_MEASUREMENT_NAME] = (time.time(), 47)
        assert pull_udp_handler._old_data(FIRTS_MEASUREMENT_NAME) is False

    def test_old_data_with_xy_data(self, pull_udp_handler, sockets_data_single):
        """Test the _old_data xy data case"""
        sockets_data_single[PORT]['type'] = 'data'

        # Test without a timeout
        sockets_data_single[PORT]['timeouts'] = {}
        assert pull_udp_handler._old_data(FIRTS_MEASUREMENT_NAME) is False

        # Test with timeout and old data
        sockets_data_single[PORT]['timeouts'] = {FIRTS_MEASUREMENT_NAME: 1.0}
        sockets_data_single[PORT]['timestamps'] = {FIRTS_MEASUREMENT_NAME: time.time() - 2.0}
        assert pull_udp_handler._old_data(FIRTS_MEASUREMENT_NAME) is True

        # Test with timeout and new data
        sockets_data_single[PORT]['timestamps'] = {FIRTS_MEASUREMENT_NAME: time.time()}
        assert pull_udp_handler._old_data(FIRTS_MEASUREMENT_NAME) is False

    def test_old_data_unkonwn_type(self, pull_udp_handler, sockets_data_single):
        """Test the old data unknown type case"""
        sockets_data_single[PORT]['type'] = 'nonsense type'
        with pytest.raises(NotImplementedError):
            pull_udp_handler._old_data(FIRTS_MEASUREMENT_NAME)


class TestCommonDataPullSocket(object):
    """Test the TestCommonDataPullSocket"""

    # pylint: disable=too-many-arguments
    @pytest.mark.parametrize("init_timeouts", [True, False],
                             ids=['init_timeout_True', 'init_timeout_False'])
    @pytest.mark.parametrize("check_activity", [True, False],
                             ids=['check_activity_T', 'check_activity_F'])
    @pytest.mark.parametrize("timeouts", [1.0, [3.0, 5.0]],
                             ids=['single_timeout', 'timeout_list'])
    def test_init(self, cdps_init_args, udp_server, clean_data, init_timeouts, timeouts,
                  check_activity):
        """Test assigning name

        cdps is short for "common data pull socket"
        """
        cdps_init_args.update({
            'init_timeouts': init_timeouts,
            'timeouts': timeouts,
            'check_activity': check_activity,
        })

        # Setup server dummy and init socket
        udp_server.return_value = 'SERVER_DUMMY'
        sock = CommonDataPullSocket(**cdps_init_args)

        # Check that thread is daemon and that the port is set
        assert sock.daemon is True
        assert sock.port == PORT

        # get config dict
        config = clean_data[PORT]

        # Check that the configuration dict has the correct keys
        expected_keys = {'codenames', 'data', 'name', 'activity'}
        if cdps_init_args['init_timeouts']:
            expected_keys.add('timeouts')
        assert set(config.keys()) == expected_keys

        # Check common config values
        assert config['codenames'] == list(cdps_init_args['codenames'])
        assert config['name'] == cdps_init_args['name']
        assert config['activity']['check_activity'] == cdps_init_args['check_activity']
        assert config['activity']['activity_timeout'] == cdps_init_args['activity_timeout']
        assert abs(time.time() - config['activity']['last_activity']) < 1E-2

        # Check data initialization with defaults
        assert config['data'] ==\
            {name: (cdps_init_args['default_x'], cdps_init_args['default_y'])
             for name in CODENAMES}

        # Check init of timeouts
        if init_timeouts:
            # If timeouts is given as a single number, make a list
            if not isinstance(timeouts, collections.Iterable):
                timeouts = [timeouts] * len(CODENAMES)
            timeouts = dict(zip(CODENAMES, timeouts))
            assert config['timeouts'] == timeouts

        # Check that SocketServer.UDPServer is called
        udp_server.assert_called_once_with(('', PORT), cdps_init_args['handler_class'])
        assert sock.server == 'SERVER_DUMMY'

    def test_port_already_used_error(self, cdps_init_args, udp_server, clean_data):
        """Test that reusing a port"""
        clean_data[PORT] = 'Anything here'
        with pytest.raises(ValueError) as exception:
            CommonDataPullSocket(**cdps_init_args)
        assert str(exception.value) == 'A UDP server already exists on port: {}'.format(PORT)


    def test_bad_timeout_length_error(self, cdps_init_args, udp_server, clean_data):
        """Test that giving a bad number of timeouts will raise an exception"""
        cdps_init_args['timeouts'] = [9.0] * 5
        with pytest.raises(ValueError) as exception:
            CommonDataPullSocket(**cdps_init_args)
        expected_error_msg = 'If a list of timeouts is supplied, it must have as many items '\
                             'as there are in codenames'
        assert str(exception.value) == expected_error_msg

    def test_repeat_codename_error(self, cdps_init_args, udp_server, clean_data):
        """Test that a repeated codename gives an error"""
        cdps_init_args['codenames'] = [FIRTS_MEASUREMENT_NAME] * 2
        with pytest.raises(ValueError) as exception:
            CommonDataPullSocket(**cdps_init_args)
        expected_error_msg = 'Codenames must be unique; \'{}\' '\
                             'is present more than once'.format(FIRTS_MEASUREMENT_NAME)
        assert str(exception.value) == expected_error_msg

    def test_bad_char_in_codename_error(self, cdps_init_args, udp_server, clean_data):
        """Test that a bad char in a codename gives an error"""
        cdps_init_args['codenames'][0] = FIRTS_MEASUREMENT_NAME + '#'
        with pytest.raises(ValueError) as exception:
            CommonDataPullSocket(**cdps_init_args)
        expected_error_msg = 'The character \'#\' is not allowed in the codenames'
        assert str(exception.value) == expected_error_msg

    def test_udp_server_exception(self, cdps_init_args, udp_server, clean_data):
        """Test that if UDPServer raises we either intercept of code is 98 or re raise"""
        class MyException(Exception):
            """Exception with errno"""
            def __init__(self, msg, errno):
                super(MyException, self).__init__(msg)
                self.errno = errno

        # Monkey-patch socket.error
        original_error = socket.error
        socket.error = MyException

        # If errno is 97, we re-raise the exception
        udp_server.side_effect = MyException('BOOM', 97)
        with pytest.raises(MyException):
            CommonDataPullSocket(**cdps_init_args)

        del clean_data[PORT]
        udp_server.side_effect = MyException('BOOM', 98)
        with pytest.raises(sockets.PortStillReserved):
            CommonDataPullSocket(**cdps_init_args)

        # Reverse monkey patch
        socket.error = original_error

    def test_run(self, cdps_init_args, clean_data):
        """Test the run method"""
        sock = CommonDataPullSocket(**cdps_init_args)
        sock.server = mock.MagicMock()
        sock.run()
        sock.server.serve_forever.assert_called_once_with()

    def test_stop(self, cdps_init_args, clean_data):
        """Test the stop method"""
        sock = CommonDataPullSocket(**cdps_init_args)
        assert PORT in clean_data
        sock.server = mock.MagicMock()
        sock.stop()

        # Check that the server shutdown methods has been called ...
        sock.server.shutdown.assert_called_once_with()

        # ... and that the port has been removed from data
        assert not PORT in clean_data

    def test_poke(self, cdps_init_args, clean_data):
        """Test the poke method"""
        sock = CommonDataPullSocket(**cdps_init_args)
        # Mock time and check that it is written to last_activity
        with mock.patch('time.time') as time_:
            time_.return_value = 12345678.9
            sock.poke()
        # Poke should set last_activity to now
        assert clean_data[PORT]['activity']['last_activity'] == 12345678.9
        time_.assert_called_once_with()


class TestDataPullSocket(object):
    """Test the DataPullSocket"""

    def test_init_super_calls(self, clean_data, udp_server):
        """Test the __init__ method"""
        # Monkey patch CommonDataPullSocket.__init__ with memory version
        original_init = CommonDataPullSocket.__init__
        def trace_init(*args, **kwargs):
            """An init function with memory"""
            trace_init.called = True
            trace_init.call_spec = args, kwargs
            original_init(*args, **kwargs)
        trace_init.called = False
        CommonDataPullSocket.__init__ = trace_init
        DataPullSocket(NAME, CODENAMES)
        assert trace_init.called
        assert trace_init.call_spec[0][1:] == (NAME, CODENAMES)
        assert trace_init.call_spec[1] == {
            'port':9010, 'default_x': 0.0,
            'default_y' :0.0, 'timeouts': None,
            'check_activity': True, 'activity_timeout': 900
        }

        # With other key word arguments
        trace_init.call_spec = None
        DataPullSocket(NAME, CODENAMES, port=1234, default_x=56.0, default_y=7.7, timeouts=9.0,
                       check_activity=False, activity_timeout=180)
        assert trace_init.call_spec[1] == {
            'port':1234, 'default_x': 56.0,
            'default_y' :7.7, 'timeouts': 9.0,
            'check_activity': False, 'activity_timeout': 180
        }

        # Revert monkey patch
        CommonDataPullSocket.__init__ = original_init

    @pytest.mark.parametrize("poke_on_set", [True, False],
                             ids=['poke_on_set_T', 'poke_on_set_F'])
    def test_init_properties(self, clean_data, udp_server, poke_on_set):
        """Test setting of properties"""
        sock = DataPullSocket(NAME, CODENAMES, poke_on_set=poke_on_set)
        assert clean_data[9010]['type'] == 'data'
        assert clean_data[9010]['timestamps'] == {name: 0.0 for name in CODENAMES}
        assert sock.poke_on_set == poke_on_set

    # pylint: disable=too-many-arguments
    @pytest.mark.parametrize("poke_on_set", [True, False],
                             ids=['poke_on_set_T', 'poke_on_set_F'])
    @pytest.mark.parametrize("check_activity", [True, False],
                             ids=['check_activity_T', 'check_activity_F'])
    @pytest.mark.parametrize("timestamp", [None, 12345.6],
                             ids=['timestamp_none', 'timestamp_set'])
    def test_set_point(self, clean_data, udp_server, poke_on_set, timestamp, check_activity):
        """Test the set_point method"""
        point = [5.6, 7.8]
        with mock.patch('PyExpLabSys.common.sockets.DataPullSocket.poke') as poke:
            sock = DataPullSocket(NAME, CODENAMES, poke_on_set=poke_on_set,
                                  check_activity=check_activity)
            sock.set_point(FIRTS_MEASUREMENT_NAME, [5.6, 7.8], timestamp=timestamp)

            # Test point
            assert clean_data[9010]['data'][FIRTS_MEASUREMENT_NAME] == tuple(point)

            # Test timestamp
            if timestamp is None:
                assert abs(clean_data[9010]['timestamps'][FIRTS_MEASUREMENT_NAME] - \
                           time.time()) < 1E-2
            else:
                assert clean_data[9010]['timestamps'][FIRTS_MEASUREMENT_NAME] == timestamp

            # Test poke_on_set
            if check_activity and poke_on_set:
                poke.assert_called_once_with()
            else:
                assert not poke.called


class TestDateDataPullSocket(object):
    """Test the DateDataPullSocket class"""

    def test_init_super_calls(self, clean_data, udp_server):
        """Test the __init__ method"""
        # Monkey patch CommonDataPullSocket.__init__ with memory version
        original_init = CommonDataPullSocket.__init__
        def trace_init(*args, **kwargs):
            """An init function with memory"""
            trace_init.called = True
            trace_init.call_spec = args, kwargs
            original_init(*args, **kwargs)
        trace_init.called = False
        CommonDataPullSocket.__init__ = trace_init
        DateDataPullSocket(NAME, CODENAMES)
        assert trace_init.called
        assert trace_init.call_spec[0][1:] == (NAME, CODENAMES)
        assert trace_init.call_spec[1] == {
            'port':9000, 'default_x': 0.0,
            'default_y' :0.0, 'timeouts': None,
            'check_activity': True, 'activity_timeout': 900
        }

        # With other key word arguments
        trace_init.call_spec = None
        DateDataPullSocket(NAME, CODENAMES, port=1234, default_x=56.0, default_y=7.7,
                           timeouts=9.0, check_activity=False, activity_timeout=180)
        assert trace_init.call_spec[1] == {
            'port':1234, 'default_x': 56.0,
            'default_y' :7.7, 'timeouts': 9.0,
            'check_activity': False, 'activity_timeout': 180
        }

        # Revert monkey patch
        CommonDataPullSocket.__init__ = original_init

    @pytest.mark.parametrize("poke_on_set", [True, False],
                             ids=['poke_on_set_T', 'poke_on_set_F'])
    def test_init_properties(self, clean_data, udp_server, poke_on_set):
        """Test setting of properties"""
        sock = DateDataPullSocket(NAME, CODENAMES, poke_on_set=poke_on_set)
        assert clean_data[9000]['type'] == 'date'
        assert sock.poke_on_set == poke_on_set

    def test_set_point_now(self, clean_data, udp_server):
        """Test setting of properties"""
        with mock.patch(SOCKETS_PATH.format('DateDataPullSocket.set_point')) as set_point:
            with mock.patch('time.time') as time:
                time.return_value = 999.0
                sock = DateDataPullSocket(NAME, CODENAMES)
                point = (4.5, 6.7)
                sock.set_point_now(FIRTS_MEASUREMENT_NAME, point)
                set_point.assert_called_once_with(FIRTS_MEASUREMENT_NAME, (999.0, point))

    # pylint: disable=too-many-arguments
    @pytest.mark.parametrize("poke_on_set", [True, False],
                             ids=['poke_on_set_T', 'poke_on_set_F'])
    @pytest.mark.parametrize("check_activity", [True, False],
                             ids=['check_activity_T', 'check_activity_F'])
    def test_set_point(self, clean_data, udp_server, poke_on_set, check_activity):
        """Test the set_point method"""
        point = [5.6, 7.8]
        with mock.patch('PyExpLabSys.common.sockets.DateDataPullSocket.poke') as poke:
            sock = DateDataPullSocket(NAME, CODENAMES, poke_on_set=poke_on_set,
                                      check_activity=check_activity)
            sock.set_point(FIRTS_MEASUREMENT_NAME, [5.6, 7.8])

            # Test point
            assert clean_data[9000]['data'][FIRTS_MEASUREMENT_NAME] == tuple(point)

            # Test poke_on_set
            if check_activity and poke_on_set:
                poke.assert_called_once_with()
            else:
                assert not poke.called


class TestPushUDPHandler(object):
    """Test the PushUDPHandler"""

    raw_wn_request = b'raw_wn#meas1:float:47.0;string1:str:Hallo World!'
    json_wn_request = b'json_wn#{"meas1": 4.7, "string1": "Hallo World!"}'
    set_data_dict = {'last': None, 'last_time': None, 'updated': {'meas1': 66},
                     'updated_time': None, 'action': None}
    test_data = {'meas1': 4.7, 'string1': 'Hallo World!'}

    def test_port(self, mocket, server, clean_data):
        """Test setting the port"""
        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler.handle')):
            handler = PushUDPHandler((b'dummy_request', mocket), CLIENT_ADDRESS, server)
        handler.handle()
        assert handler.port == 9876

    def test_handle_name(self, mocket, server, clean_data):
        """Test the handle name case"""
        request = b'name'
        clean_data[9876] = {'name': SOCKET_NAME}

        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler.handle')):
            handler = PushUDPHandler((request, mocket), CLIENT_ADDRESS, server)

        handler.handle()
        expected = '{}#{}'.format(sockets.PUSH_RET, SOCKET_NAME)
        mocket.sendto.assert_called_once_with(expected.encode('ascii'), CLIENT_ADDRESS)

    def test_handle_commands(self, mocket, server, clean_data):
        """Test the handle commands case"""
        request = b'commands'

        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler.handle')):
            handler = PushUDPHandler((request, mocket), CLIENT_ADDRESS, server)

        handler.handle()
        expected = '{}#[\"json_wn#\", \"raw_wn#\", \"name\", \"status\", \"commands\"]'.\
                   format(sockets.PUSH_RET)
        mocket.sendto.assert_called_once_with(expected.encode('ascii'), CLIENT_ADDRESS)

    def test_handle_status(self, mocket, server, clean_data):
        """Test the handle status case"""
        request = b'status'

        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler.handle')):
            handler = PushUDPHandler((request, mocket), CLIENT_ADDRESS, server)

        # Set up mocks for SYSTEM_STATUS and socket_server_status
        with mock.patch(SOCKETS_PATH.format('SYSTEM_STATUS')) as system_status:
            system_status.complete_status.return_value = 1
            with mock.patch(SOCKETS_PATH.format('socket_server_status')) as\
                 socket_server_status:
                socket_server_status.return_value = 2

                handler.handle()

                # Test the expected output
                expected = {'system_status': 1, 'socket_server_status': 2}
                args = tuple(mocket.sendto.call_args[0])
                assert args[1] == CLIENT_ADDRESS
                assert json.loads(args[0].decode('ascii')) == expected

    def test_handle_no_hash(self, mocket, server, clean_data):
        """Test the case, where the command is not any of the previous ones and it does not
        contain an #
        """
        request = b'some_bad_command'

        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler.handle')):
            handler = PushUDPHandler((request, mocket), CLIENT_ADDRESS, server)

        handler.handle()
        expected = '{}#{}'.format(sockets.PUSH_ERROR, sockets.UNKNOWN_COMMAND)
        mocket.sendto.assert_called_once_with(expected.encode('ascii'), CLIENT_ADDRESS)

    def test_handle_json_wn(self, mocket, server, clean_data):
        """Test the handle json with names case"""
        json_return_value = 'json_wn_return_value'

        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler.handle')):
            handler = PushUDPHandler((self.json_wn_request, mocket), CLIENT_ADDRESS, server)

        # Mock _json_with_names and call handle
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler._json_with_names')) as json_wn:
            json_wn.return_value = json_return_value
            handler.handle()
            json_wn.assert_called_once_with('{"meas1": 4.7, "string1": "Hallo World!"}')

        mocket.sendto.assert_called_once_with(json_return_value.encode('ascii'),
                                              CLIENT_ADDRESS)

    def test_handle_raw_wn(self, mocket, server, clean_data):
        """Test the handle raw with names case"""
        raw_return_value = 'raw_wn_return_value'

        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler.handle')):
            handler = PushUDPHandler((self.raw_wn_request, mocket), CLIENT_ADDRESS, server)

        # Mock _raw_with_names and call handle
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler._raw_with_names')) as raw_wn:
            raw_wn.return_value = raw_return_value
            handler.handle()
            raw_wn.assert_called_once_with('meas1:float:47.0;string1:str:Hallo World!')

        mocket.sendto.assert_called_once_with(raw_return_value.encode('ascii'),
                                              CLIENT_ADDRESS)

    def test_handle_unknown(self, mocket, server, clean_data):
        """Test the handle unknown command case"""
        request = b'unkonwn_command'
        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler.handle')):
            handler = PushUDPHandler((request, mocket), CLIENT_ADDRESS, server)
        handler.handle()

        expected = '{}#{}'.format(sockets.PUSH_ERROR, sockets.UNKNOWN_COMMAND)
        mocket.sendto.assert_called_once_with(expected.encode('ascii'), CLIENT_ADDRESS)

    @pytest.mark.parametrize("method_and_request",
        (('_json_with_names', json_wn_request), ('_raw_with_names', raw_wn_request)),
        ids=['json_with_names', 'raw_with_names'])
    def test_handle_wn_exceptions(self, mocket, server, clean_data, method_and_request):
        """Test the handle json and raw with name exception case"""
        method, request = method_and_request
        msg = 'You messed up!' + method  # Create msg unique to the parametrisized case

        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler.handle')):
            handler = PushUDPHandler((request, mocket), CLIENT_ADDRESS, server)

        # Mock the with name method to raise a ValueError
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler.' + method)) as method:
            method.side_effect = ValueError(msg)
            handler.handle()

        expected = '{}#{}'.format(sockets.PUSH_ERROR, msg)
        mocket.sendto.assert_called_once_with(expected.encode('ascii'), CLIENT_ADDRESS)

    def test_raw_with_names(self, clean_data, push_udp_handler):
        """Test the _raw_with_names method"""
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler._set_data')) as set_data:
            set_data.return_value = ANY_RETURN
            argument = self.raw_wn_request.decode('ascii').split('#')[1]
            assert push_udp_handler._raw_with_names(argument) == ANY_RETURN
            set_data.assert_called_once_with({'meas1': 47.0, 'string1': 'Hallo World!'})

    def test_raw_with_names_exceptions(self, clean_data, push_udp_handler):
        """Test the _raw_with_names exceptions"""
        # Test exception for a bad format
        with pytest.raises(ValueError) as exception:
            push_udp_handler._raw_with_names('mymeas:int8')
        assert str(exception.value).startswith('The data part ')
        assert str(exception.value).endswith(
            ' did not match the expected format of 3 parts divided by \':\'')

        # Test the exception for an unknown type
        with pytest.raises(ValueError) as exception:
            push_udp_handler._raw_with_names('mymeas:longint:8')
        assert str(exception.value).startswith(
            'The data type \'longint\' is unknown. Only ')
        assert str(exception.value).endswith(' are allowed')

        # Test the exception when the type function cannot convert
        with pytest.raises(ValueError) as exception:
            push_udp_handler._raw_with_names('mymeas:float:jkljkl')
        assert str(exception.value).startswith('Unable to convert values to \'')

    def test_json_with_names(self, clean_data, push_udp_handler):
        """Test the _json_with_names method"""
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler._set_data')) as set_data:
            set_data.return_value = ANY_RETURN
            argument = self.json_wn_request.decode('ascii').split('#')[1]
            assert push_udp_handler._json_with_names(argument) == ANY_RETURN
            set_data.assert_called_once_with({'meas1': 4.7, 'string1': 'Hallo World!'})

    def test_json_with_names_exceptions(self, clean_data, push_udp_handler):
        """Test the _json_with_names exceptions"""
        # Test the not json exception
        with pytest.raises(ValueError) as exception:
            push_udp_handler._json_with_names('dsd')
        assert str(exception.value).startswith('The string ')
        assert str(exception.value).endswith(' could not be decoded as JSON')

        # Test the not dict exception
        with pytest.raises(ValueError) as exception:
            push_udp_handler._json_with_names('"dsd"')
        assert str(exception.value).startswith('The object \'')
        assert str(exception.value).endswith(
            ' returned after decoding the JSON string is not a dict')

    def test_set_data_main(self, clean_data, push_udp_handler):
        """Test the _set_data main data set in DATA"""
        # Setup
        clean_data[PORT] = dict(self.set_data_dict)
        data = {'meas1': 4.7, 'string1': 'Hallo World!'}
        push_udp_handler.port = PORT

        # Set and test
        with mock.patch('time.time') as mocktime:
            mocktime.return_value = 789.0
            push_udp_handler._set_data({'meas1': 4.7, 'string1': 'Hallo World!'})
        assert clean_data[PORT]['last'] == data
        assert clean_data[PORT]['last_time'] == 789.0
        assert clean_data[PORT]['updated'] == data
        assert clean_data[PORT]['updated_time'] == 789.0

    @pytest.mark.parametrize('action', ['enqueue', 'callback_async', 'nonaction'],
                             ids=['enqueue', 'callback_async', 'nonaction'])
    def test_set_data_main_enqueue(self, clean_data, push_udp_handler, action):
        """Test the _set_data enqueue data set in DATA"""
        # Setup
        clean_data[PORT] = dict(self.set_data_dict)
        clean_data[PORT]['action'] = action
        clean_data[PORT]['queue'] = mock.MagicMock()
        push_udp_handler.port = PORT

        # Set and test
        push_udp_handler._set_data(self.test_data)
        if action == 'nonaction':
            assert clean_data[PORT]['queue'].put.call_count == 0
        else:
            clean_data[PORT]['queue'].put.assert_called_once_with(self.test_data)

    @pytest.mark.parametrize(
        'formatter', ['_format_return_json', '_format_return_raw', '_format_return_string'],
        ids=['format_return_json', 'format_return_raw', 'format_return_string'])
    def test_set_data_callback_direct(self, clean_data, push_udp_handler, formatter):
        """Test the set data callback_direct case"""
        # Setup
        cbmock = mock.MagicMock(name='mycallback')
        cbmock.return_value = 'callback_return_value'
        clean_data[PORT] = dict(self.set_data_dict)
        clean_data[PORT]['action'] = 'callback_direct'
        clean_data[PORT]['callback'] = cbmock
        clean_data[PORT]['return_format'] = formatter.split('_')[-1]
        push_udp_handler.port = PORT

        # Call _set_data and check the callback
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler.' + formatter)) as formatter:
            formatter.return_value = ANY_RETURN
            assert push_udp_handler._set_data(self.test_data) == ANY_RETURN
            cbmock.assert_called_once_with(self.test_data)
            formatter.assert_called_once_with('callback_return_value')

    def test_set_data_bad_return_format(self, clean_data, push_udp_handler):
        """Test the _set_data callback raise exception case"""
        # Setup
        cbmock = mock.MagicMock(name='mycallback')
        cbmock.return_value = 'callback_return_value'
        clean_data[PORT] = dict(self.set_data_dict)
        clean_data[PORT]['action'] = 'callback_direct'
        clean_data[PORT]['return_format'] = 'unknown_return_format'
        clean_data[PORT]['callback'] = cbmock
        push_udp_handler.port = PORT

        # Call _set_data and check that it gives the correct error
        expected = '{}#Bad return format. REPORT AS BUG.'.format(sockets.PUSH_ERROR)
        assert push_udp_handler._set_data(self.test_data) == expected

    def test_set_data_cb_raise(self, clean_data, push_udp_handler):
        """Test the _set_data callback raise exception case"""
        # Setup
        cbmock = mock.MagicMock(name='mycallback')
        cbmock.side_effect = ValueError('You messed up!')
        clean_data[PORT] = dict(self.set_data_dict)
        clean_data[PORT]['action'] = 'callback_direct'
        clean_data[PORT]['callback'] = cbmock
        clean_data[PORT]['return_format'] = 'json'
        push_udp_handler.port = PORT

        # Call _set_data and check that callback raised excep. is passed on as error
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler._format_return_json')):
            expected = '{}#You messed up!'.format(sockets.PUSH_EXCEP)
            assert push_udp_handler._set_data(self.test_data) == expected

    def test_set_data_formatter_raise(self, clean_data, push_udp_handler):
        """Test the _set_data callback formatter raise exception case"""
        # Setup
        cbmock = mock.MagicMock(name='mycallback')
        cbmock.return_value = ANY_RETURN
        clean_data[PORT] = dict(self.set_data_dict)
        clean_data[PORT]['action'] = 'callback_direct'
        clean_data[PORT]['callback'] = cbmock
        clean_data[PORT]['return_format'] = 'json'
        push_udp_handler.port = PORT

        # Call _set_data and check that formatter raised excep. is passed on as error
        with mock.patch(SOCKETS_PATH.format('PushUDPHandler._format_return_json')) as\
             formatter:
            formatter.side_effect = ValueError('You messed up!')
            expected = '{}#You messed up!'.format(sockets.PUSH_EXCEP)
            assert push_udp_handler._set_data(self.test_data) == expected

    def test_format_return_json(self, clean_data, push_udp_handler):
        """Test the _format_return_json method"""
        # Test success case
        with mock.patch('json.dumps') as dumps:
            dumps.return_value = ANY_RETURN
            expected = '{}#{}'.format(sockets.PUSH_RET, ANY_RETURN)
            assert push_udp_handler._format_return_json(self.test_data) == expected

        # Test json.dumps exception case
        with mock.patch('json.dumps') as dumps:
            dumps.side_effect = TypeError('You messed up!')
            expected = '{}#You messed up!'.format(sockets.PUSH_EXCEP)
            assert push_udp_handler._format_return_json(self.test_data) == expected

    def test_format_return_string(self, clean_data, push_udp_handler):
        """Test the _format_return_string method"""
        obj = mock.MagicMock()
        obj.__str__.return_value = ANY_RETURN
        expected = '{}#{}'.format(sockets.PUSH_RET, ANY_RETURN)
        assert push_udp_handler._format_return_string(obj) == expected

    def test_format_return_string_raise(self, clean_data, push_udp_handler):
        """Test the _format_return_string method str raise exception"""
        obj = mock.MagicMock()
        # __str__ is also called for the logging call, therefore, make it return nicely on the
        # first call and raise exception on the second
        obj.__str__.side_effect = [AttributeError('You messed up!')]
        expected = '{}#You messed up!'.format(sockets.PUSH_EXCEP)
        assert push_udp_handler._format_return_string(obj) == expected

    @pytest.mark.parametrize('input_', ({'a': 8}, [3, 4]), ids=('dict', 'list'))
    def test_format_return_raw(self, clean_data, push_udp_handler, input_):
        """Test the _format_return_raw case

        Parametrisized to test subcall to both _format_return_raw_list and
        _format_return_raw_dict
        """
        called_formatter_name = 'PushUDPHandler._format_return_raw_' +\
                                input_.__class__.__name__
        with mock.patch(SOCKETS_PATH.format(called_formatter_name)) as called_formatter:
            called_formatter.return_value = ANY_RETURN
            assert push_udp_handler._format_return_raw(input_) == ANY_RETURN

    def test_format_return_raw_none(self, clean_data, push_udp_handler):
        """Test the _format_return_raw format None case"""
        assert push_udp_handler._format_return_raw(None) == '{}#None'.format(sockets.PUSH_RET)

    @pytest.mark.parametrize('input_', ({'a': 8}, [3, 4]), ids=('dict', 'list'))
    def test_format_return_raw_raise(self, clean_data, push_udp_handler, input_):
        """Test the _format_return_raw raise from formatter"""
        # Test that exceptions in the formatters are passed on
        method_name = 'PushUDPHandler._format_return_raw_{}'.format(input_.__class__.__name__)
        with mock.patch(SOCKETS_PATH.format(method_name)) as formatter:
            formatter.side_effect = Exception('You messed up!')
            expected = '{}#Raw conversion failed with message:You messed up!'.\
                format(sockets.PUSH_EXCEP)
            assert push_udp_handler._format_return_raw(input_) == expected

        # Test that using a wrong input type gives an error
        expected = '{}#Raw conversion failed with message:Return value must be a dict or '\
                   'list with return format \'raw\''.format(sockets.PUSH_EXCEP)
        assert push_udp_handler._format_return_raw(7) == expected

    def test_format_return_raw_dict(self, clean_data, push_udp_handler):
        """Test the _format_return_raw_dict method

        It is expected to turn an input on the form:
            {'answer': 42, 'values': [42, 47], 'answer_good': False}
        into:
            'answer:int:42;values:int:42,47:answer_good:bool:False'
        """
        # Test valid input
        inputs = (
            {'answer': 42, 'values': [42, 47], 'answer_good': False},
            {'mystr': 'Live long and prosper', 'myfloat': 47.0},
            {'list_of_floats': [1.0, 2.0, 3.0e-18, 4.0, 5.0]}
        )
        replies = (
            ('answer:int:42', 'values:int:42,47', 'answer_good:bool:False'),
            ('mystr:str:Live long and prosper', 'myfloat:float:47.0'),
            ('list_of_floats:float:1.0,2.0,3e-18,4.0,5.0',)
        )
        for input_, expected_reply in zip(inputs, replies):
            # Get the output
            reply = push_udp_handler._format_return_raw_dict(input_)

            # Check that the output starts with 'RET#
            assert reply.startswith(sockets.PUSH_RET + '#')

            # Break of the beginning and split the rest into data chunks
            reply_chunks = set(reply.split('#', 1)[1].split(';'))

            # Check that each chunk is in the expected results and pop it from there
            for chunk in expected_reply:
                assert chunk in reply_chunks
                reply_chunks.remove(chunk)

            # Check that there are noe expected chunks left
            assert len(reply_chunks) == 0

        # Test invalid input, differing types in lists
        expected_exception = 'With return format raw, value in list must have same type'
        with pytest.raises(ValueError) as exception:
            push_udp_handler._format_return_raw_dict({'mylist': [1, 47.0]})
        assert str(exception.value) == expected_exception

        # Test invalid type
        expected_exception = ('With return format raw, the item type can only be one of '
                              '\'int\', \'float\', \'bool\' and \'str\'. Object: \'(1+3j)\' '
                              'is of type: {}').format(type(1 + 3j).__name__)
        with pytest.raises(TypeError) as exception:
            push_udp_handler._format_return_raw_dict({'mycomplex': 1 + 3j})
        assert str(exception.value) == expected_exception

    def test_format_return_raw_list(self, clean_data, push_udp_handler):
        """Test the _format_return_raw_list method

        It is expected to turn an input on the form:
            [[7.0, 42.0], [7.5, 45.5], [8.0, 47.0]]
        into:
            'RET#float:7.0,42.0&7.5,45.5&8.0,47.0'
        """
        # Test valid input
        inputs = (
            [[7.0, 42.0], [7.5, 45.5], [8.0, 47.0]],
            [[1, 2], [3, 4], [5 * 10**6, 9 * 10**9]]
        )
        replies = (
            ('7.0,42.0', '7.5,45.5', '8.0,47.0'),
            ('1,2', '3,4', '5000000,9000000000'),
        )
        for input_, expected_reply in zip(inputs, replies):
            # Get the return value
            reply = push_udp_handler._format_return_raw_list(input_)

            # Check that the return startswith RET#<type>:
            assert reply.startswith(sockets.PUSH_RET + '#' + type(input_[0][0]).__name__)

            # Break of the beginning, and break the rest into data parrs
            reply_chunks = set(reply.split(':', 1)[1].split('&'))

            # Check that each chunk in the reply is expected
            for chunk in expected_reply:
                assert chunk in reply_chunks
                reply_chunks.remove(chunk)

            # Check that there are no expected chunks left
            assert len(reply_chunks) == 0

        # Check for error on differing types in the lists
        with pytest.raises(ValueError) as exception:
            push_udp_handler._format_return_raw_list([[1.0, 2], [3.0, 4.0]])

        expected = 'With return format raw on a list of lists, all values '\
            ' in list must have same type'
        assert str(exception.value).startswith(expected)

        # Check for error on invalid type
        with pytest.raises(TypeError) as exception:
            push_udp_handler._format_return_raw_list([[1.0j, 2j], [3.0j, 4.0j]])

        expected_error_msg = 'With return format raw, the item type can only be one '\
                'of \'int\', \'float\', \'bool\' and \'str\'. The type is: '
        assert str(exception.value).startswith(expected_error_msg)


class TestDataPushSocket(object):
    """Test the DataPushSocket"""

    @pytest.mark.parametrize('port', [8500, 8765])
    def test_init_common(self, clean_data, udp_server, port):
        """Test the common initializations in init"""
        with mock.patch('time.time') as time_:
            time_.return_value = 12345.6
            data_push_socket = DataPushSocket(NAME, port=port)

        # Check (internal) properties
        assert data_push_socket.port == port
        assert data_push_socket.daemon is True
        assert data_push_socket._stop is False
        assert data_push_socket._callback_thread is None

        # Check udp_socket_server init
        udp_server.assert_called_once_with(('', port), PushUDPHandler)

        # Check socket config in DATA
        assert port in clean_data
        expected_values = {
            'action': 'store_last', 'last': None, 'type': 'push', 'updated': {},
            'last_time': None, 'updated_time': None, 'name': NAME,
            'activity': {
                'check_activity': False,
                'activity_timeout': 900,
                'last_activity': 12345.6,
            }
        }
        assert clean_data[port] == expected_values

    def test_init_bad_queue_raise(self, clean_data, udp_server):
        """Test that using the queue argument is only allowed with enqueue action"""
        with pytest.raises(ValueError) as exception:
            DataPushSocket(NAME, queue='myqueue')
        assert str(exception.value) == 'The \'queue\' argument can only be used when the '\
            'action is \'enqueue\''

    def test_init_bad_callback_raise(self, clean_data, udp_server):
        """Test that using the callback argument is only allowed with the callback actions"""
        with pytest.raises(ValueError) as exception:
            DataPushSocket(NAME, callback='mycallback')
        assert str(exception.value) == 'The \'callback\' argument can only be used when '\
            'the action is \'callback_async\' or \'callback_direct\''

    def test_init_noncallable_cb_raise(self, clean_data, udp_server):
        """Test that supplying non-callable callback raises"""
        with pytest.raises(ValueError) as exception:
            DataPushSocket(NAME, action='callback_async', callback='mycallback')
        assert str(exception.value) == 'Value for callback: \'mycallback\' is not callable'

    def test_init_bad_ret_format_raise(self, clean_data, udp_server):
        """Test that giving a bad return format raises"""
        with pytest.raises(ValueError) as exception:
            DataPushSocket(NAME, return_format='foobar')
        assert str(exception.value) == 'The \'return_format\' argument may only be one of '\
            'the \'json\', \'raw\' or \'string\' values'

    @pytest.mark.parametrize('queue', ('myqueue', None), ids=('queue_set', 'queue_not_set'))
    def test_init_enqueue(self, clean_data, udp_server, queue):
        """Test that choosing enqueue is properly setting the queue"""
        with mock.patch(QUEUE_CLASS_PATH) as mock_queue:
            mock_queue.return_value = 'queue_from_Queue'
            DataPushSocket(NAME, port=PORT, action='enqueue', queue=queue)
        assert clean_data[PORT]['action'] == 'enqueue'
        if queue == 'myqueue':
            assert clean_data[PORT]['queue'] == 'myqueue'
        else:
            mock_queue.assert_called_once_with()
            assert clean_data[PORT]['queue'] == 'queue_from_Queue'

    def test_init_callback_async(self, clean_data, udp_server):
        """Test that choosing callback_async is properly setup"""
        def callback_func():
            """Small pass callback function"""
            pass

        # Setup
        with mock.patch(QUEUE_CLASS_PATH) as mock_queue:
            mock_queue.return_value = 'my_queue'
            with mock.patch(SOCKETS_PATH.format('CallBackThread')) as callback_thread:
                callback_thread.return_value = 'my_callback_thread'
                data_push_socket = DataPushSocket(NAME, port=PORT, action='callback_async',
                                                  callback=callback_func)

        # Check that Queue was initialized and the callback called
        mock_queue.assert_called_once_with()
        callback_thread.assert_called_once_with('my_queue', callback_func)
        assert clean_data[PORT]['action'] == 'callback_async'
        assert clean_data[PORT]['queue'] == 'my_queue'
        assert data_push_socket._callback_thread == 'my_callback_thread'

    @pytest.mark.parametrize('return_format', ('json', 'raw', 'string'),
                             ids=('json', 'raw', 'string'))
    def test_init_callback_direct(self, clean_data, udp_server, return_format):
        """Test that choosing callback_direct if properly setup"""
        def callback_func():
            """Small pass callback function"""
            pass
        DataPushSocket(NAME, port=PORT, action='callback_direct', callback=callback_func,
                       return_format=return_format)
        assert clean_data[PORT]['callback'] == callback_func
        assert clean_data[PORT]['return_format'] == return_format

    def test_init_bad_action_raise(self, clean_data, udp_server):
        """Test that initializing with a bad action raises"""
        with pytest.raises(ValueError) as exception:
            DataPushSocket(NAME, action='foobar')
        assert str(exception.value) == 'Unknown action \'foobar\'. Must be one of: '\
            '[\'store_last\', \'enqueue\', \'callback_async\', \'callback_direct\']'

    def test_udp_server_exception(self, clean_data, udp_server):
        """Test that if UDPServer raises we either intercept if code is 98 or re-raise"""
        class MyException(Exception):
            """Exception with errno"""
            def __init__(self, msg, errno):
                super(MyException, self).__init__(msg)
                self.errno = errno

        # Monkey-patch socket.error
        original_error = socket.error
        socket.error = MyException

        # If errno is 97, we re-raise the exception
        udp_server.side_effect = MyException('BOOM', 97)
        with pytest.raises(MyException):
            DataPushSocket(NAME, port=PORT)

        # If it is 98, we raise a custom exception
        udp_server.side_effect = MyException('BOOM', 98)
        with pytest.raises(sockets.PortStillReserved):
            DataPushSocket(NAME, port=PORT)

        # Reverse monkey patch
        socket.error = original_error

    @pytest.mark.parametrize('action_and_callback',
                             (('enqueue', None), ('callback_async', mock.MagicMock())),
                             ids=('enqueue', 'callback_async'))
    def test_run(self, clean_data, udp_server, action_and_callback):
        """Test the run method"""
        action, callback = action_and_callback
        with mock.patch(SOCKETS_PATH.format('CallBackThread')):
            data_push_socket = DataPushSocket(NAME, action=action, callback=callback)

        # Set up mocks
        data_push_socket._callback_thread = mock.MagicMock()
        data_push_socket.server = mock.MagicMock()

        # Call and check external calls
        data_push_socket.run()
        if action == 'callback_async':
            data_push_socket._callback_thread.start.assert_called_once_with()
        data_push_socket.server.serve_forever.assert_called_once_with()

    @pytest.mark.parametrize('action_and_callback',
                             (('enqueue', None), ('callback_async', mock.MagicMock())),
                             ids=('enqueue', 'callback_async'))
    def test_stop(self, clean_data, udp_server, action_and_callback):
        """Test the stop method"""
        # Setup, and check that the socket was added to DATA
        action, callback = action_and_callback
        assert PORT not in clean_data
        with mock.patch(SOCKETS_PATH.format('CallBackThread')):
            data_push_socket = DataPushSocket(NAME, port=PORT, action=action,
                                              callback=callback)
        assert PORT in clean_data

        # Set up mocks
        data_push_socket._callback_thread = mock.MagicMock()
        data_push_socket.server = mock.MagicMock()

        # Call and check external calls
        with mock.patch('time.sleep') as sleep:
            data_push_socket.stop()
        if action == 'callback_async':
            data_push_socket._callback_thread.stop.assert_called_once_with()
        data_push_socket.server.shutdown.assert_called_once_with()
        sleep.assert_has_calls([mock.call(0.1)] * 2)
        # Check that config is removed from data
        assert PORT not in clean_data

    def test_queue(self, clean_data, udp_server):
        """Test the queue property"""
        data_push_socket = DataPushSocket(NAME, action='enqueue', queue='MyQueue')
        assert data_push_socket.queue == 'MyQueue'

    @pytest.mark.parametrize('last', (None, {'a': 5, 'b': 8.0}), ids=('None', 'point'))
    def test_last(self, clean_data, udp_server, last):
        """Test the last property

        Parametrisize cases where there was a last and not
        """
        # Setup
        data_push_socket = DataPushSocket(NAME, port=PORT)
        clean_data[PORT]['last'] = last
        clean_data[PORT]['last_time'] = 'last_time'
        returned_time, returned_last = data_push_socket.last

        # Checks
        assert returned_time == 'last_time'
        if last is None:
            assert returned_last is None
        else:
            assert returned_last is not last
            assert returned_last == last

    def test_updated(self, clean_data, udp_server):
        """Test the updates property"""
        # Setup
        data_push_socket = DataPushSocket(NAME, port=PORT)
        updated = {'a': 9.0}
        clean_data[PORT]['updated_time'] = 'mytime'
        clean_data[PORT]['updated'] = updated

        # Checks
        returned_time, returned_updated = data_push_socket.updated
        assert returned_time == 'mytime'
        assert returned_updated is not updated
        assert returned_updated == updated

    def test_set_last_to_none(self, clean_data, udp_server):
        """Test the set_last_to_none method"""
        # Setup
        data_push_socket = DataPushSocket(NAME, port=PORT)
        clean_data[PORT]['last'] = 'not_none'
        clean_data[PORT]['last_time'] = 'not_none'

        # Call and check
        data_push_socket.set_last_to_none()
        assert clean_data[PORT]['last'] is None
        assert clean_data[PORT]['last_time'] is None

    def test_clear_updated(self, clean_data, udp_server):
        """Test the clear_updated method"""
        # Setup
        data_push_socket = DataPushSocket(NAME, port=PORT)
        clean_data[PORT]['updated'] = mock.MagicMock()
        clean_data[PORT]['updated_time'] = 'not_none'

        # Call and check
        data_push_socket.clear_updated()
        clean_data[PORT]['updated'].clear.assert_called_once_with()
        assert clean_data[PORT]['updated_time'] is None

    def test_poke(self, clean_data, udp_server):
        """Test the poke method"""
        data_push_socket = DataPushSocket(NAME, port=PORT, check_activity=True)
        with mock.patch('time.time') as time_:
            time_.return_value = 12345.6
            data_push_socket.poke()
        assert clean_data[PORT]['activity']['last_activity'] == 12345.6


class TestCallBackThread(object):
    """Test the CallBackThread class"""

    def test_init(self):
        """Test init"""
        callbackthread = CallBackThread('myqueue', 'mycallback')
        assert callbackthread.daemon is True
        assert callbackthread._stop is False
        assert callbackthread.queue == 'myqueue'
        assert callbackthread.callback == 'mycallback'

    def test_run(self):
        """Test the run method"""
        queue = mock.MagicMock()
        callback = mock.MagicMock()

        # In the current implementation the callback thread can only be stopped either by
        # getting a extra item in the queue after stop or by raising an exception
        queue.get.side_effect = ['value', Exception('stop')]
        callbackthread = CallBackThread(queue, callback)
        with pytest.raises(Exception) as exception:
            callbackthread.run()

        # Assertion
        assert str(exception.value) == 'stop'
        queue.get.assert_has_calls([mock.call(True, 1)] * 2)
        callback.assert_called_once_with('value')

    def test_stop(self):
        """Test the stop method"""
        callbackthread = CallBackThread('queue', 'callback')
        assert callbackthread._stop is False
        callbackthread.stop()
        assert callbackthread._stop is True
