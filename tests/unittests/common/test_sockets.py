# pylint: disable=no-member,no-name-in-module,redefined-outer-name,protected-access,
# pylint: disable=unused-argument,no-self-use

"""This file contains unit tests for PyExpLabSys.common.sockets"""

from __future__ import unicode_literals, print_function

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
    DateDataPullSocket,
)

### Test data
SERVER_ADDRESS = '42.42.42.42'
CLIENT_ADDRESS = '47.47.47.47'
PORT = 9876
NAME = 'my name'
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


### Fixtures
@pytest.fixture
def mocket():
    """A socket fixture"""
    return mock.MagicMock()


@pytest.yield_fixture
def sockets_data_single():
    """A fixture for replaced sockets.data"""
    old_data = sockets.DATA
    sockets.DATA = SINGLE_DATA
    yield sockets.DATA
    sockets.DATA = old_data


@pytest.yield_fixture
def sockets_data_all():
    """A fixture for replaced sockets.data"""
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
    with mock.patch('PyExpLabSys.common.sockets.PullUDPHandler.handle'):
        udp_handler = PullUDPHandler(('dummy_request', mocket), CLIENT_ADDRESS, server)
        udp_handler.port = PORT
        yield udp_handler


@pytest.fixture(scope='function')
def cdps_init_args():
    """A fixture with init args for CommonDataPullSoclet"""
    return {
        'name': NAME, 'codenames': list(CODENAMES), 'port': PORT,
        'default_x': 5.0, 'default_y': 3.0, 'timeouts': 1.0,
        'check_activity': True, 'activity_timeout': 10.0,
        'handler_class': sockets.PullUDPHandler
    }


@pytest.yield_fixture
def udp_server():
    """A UDPServer fixure"""
    with mock.patch('SocketServer.UDPServer') as udp_server:
        yield udp_server


@pytest.yield_fixture
def clean_data():
    """A clean data fixture"""
    old_data = sockets.DATA
    sockets.DATA = {}
    yield sockets.DATA
    sockets.DATA = old_data


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

    single_measurement_name = 'my_measurement'
    single_data = {PORT: {'data': {single_measurement_name: (42.0, 47.0)}}}

    def test_handle_single_val_and_port(self, mocket, server):
        """Test the handle method"""
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
                _single_value.assert_called_once_with(request)
                assert not _all_values.called
                mocket.sendto.assert_called_once_with(mock_return_value, CLIENT_ADDRESS)

        assert handler.port == PORT

    def test_handle_all_value(self, mocket, server):
        """Test the handle method"""
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
                _all_values.assert_called_once_with(request)
                assert not _single_value.called
                mocket.sendto.assert_called_once_with(mock_return_value, CLIENT_ADDRESS)

    def test_single_raw(self, pull_udp_handler, sockets_data_single):
        """Test single value raw case"""
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._old_data')) as _old_data:
            _old_data.return_value = False
            assert pull_udp_handler._single_value(FIRTS_MEASUREMENT_NAME + '#raw')\
                == '42.0,47.0'
            _old_data.assert_called_once_with(FIRTS_MEASUREMENT_NAME)

    def test_single_json(self, pull_udp_handler, sockets_data_single):
        """Test single value json case"""
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._old_data')) as _old_data:
            _old_data.return_value = False
            assert pull_udp_handler._single_value(FIRTS_MEASUREMENT_NAME + '#json')\
                == '[42.0, 47.0]'
            _old_data.assert_called_once_with(FIRTS_MEASUREMENT_NAME)

    def test_single_old(self, pull_udp_handler, sockets_data_single):
        """Test the single value old data case"""
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._old_data')) as _old_data:
            _old_data.return_value = True
            assert pull_udp_handler._single_value(FIRTS_MEASUREMENT_NAME + '#raw')\
                == 'OLD_DATA'
            _old_data.assert_called_once_with(FIRTS_MEASUREMENT_NAME)
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._old_data')) as _old_data:
            _old_data.return_value = True
            assert pull_udp_handler._single_value(FIRTS_MEASUREMENT_NAME + '#json')\
                == '"OLD_DATA"'
            _old_data.assert_called_once_with(FIRTS_MEASUREMENT_NAME)

    def test_single_unknown_command(self, pull_udp_handler, sockets_data_single):
        """Test the single value unknown command case"""
        assert pull_udp_handler._single_value(FIRTS_MEASUREMENT_NAME + '#nonsense')\
                == sockets.UNKNOWN_COMMAND

    def test_all_raw(self, pull_udp_handler, sockets_data_all):
        """Test the all values raw case"""
        with mock.patch(SOCKETS_PATH.format('PullUDPHandler._old_data')) as _old_data:
            _old_data.return_value = False
            assert pull_udp_handler._all_values('raw')\
                == '42.0,47.0;17.0,1.0'
            calls = [mock.call(FIRTS_MEASUREMENT_NAME), mock.call(SECOND_MEASUREMENT_NAME)]
            _old_data.assert_has_calls(calls)

    def test_all_json(self, pull_udp_handler, sockets_data_all):
        """Test the all values json case"""
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
        """Test the all values codenames raw case"""
        expected = FIRTS_MEASUREMENT_NAME + ',' + SECOND_MEASUREMENT_NAME
        assert pull_udp_handler._all_values('codenames_raw') == expected

    def test_all_codenames_json(self, pull_udp_handler, sockets_data_all):
        """Test the all values codenames json case"""
        expected = [FIRTS_MEASUREMENT_NAME, SECOND_MEASUREMENT_NAME]
        assert json.loads(pull_udp_handler._all_values('codenames_json')) == expected

    def test_all_name(self, pull_udp_handler, sockets_data_all):
        """Test the all values name case"""
        assert pull_udp_handler._all_values('name') == NAME

    def test_all_status(self, pull_udp_handler, sockets_data_all):
        """Test the all values name case"""
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
        """Test that if UDPServer raises ???"""
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
        assert clean_data.has_key(PORT)
        sock.server = mock.MagicMock()
        sock.stop()

        # Check that the server shutdown methods has been called ...
        sock.server.shutdown.assert_called_once_with()

        # ... and that the port has been removed from data
        assert not clean_data.has_key(PORT)

    def test_poke(self, cdps_init_args, clean_data):
        """Test the poke method"""
        sock = CommonDataPullSocket(**cdps_init_args)
        clean_data[PORT]['activity']['last_activity'] = time.time() - 10.0
        sock.poke()
        # Poke should set last_activity to now
        assert abs(clean_data[PORT]['activity']['last_activity'] - time.time()) < 1E-2


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

    def test_handle_name(self, mocket, server, cases):
        """Test the handle name case"""
        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(FIXME   self.path('handle')):
            # HEEEEERE HERE FIXME
            handler = PushUDPHandler((request, mocket), CLIENT_ADDRESS, server)


    def test_handle_single_val_and_port(self, mocket, server):
        """Test the handle method"""
        return
        request = b'dummy#request'
        mock_return_value = 'mock return value'

        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(self.path('handle')):
            handler = PullUDPHandler((request, mocket), CLIENT_ADDRESS, server)

        # Test single value case
        with mock.patch(self.path('_single_value')) as _single_value:
            _single_value.return_value = mock_return_value
            with mock.patch(self.path('_all_values')) as _all_values:
                handler.handle()
                _single_value.assert_called_once_with(request)
                assert not _all_values.called
                mocket.sendto.assert_called_once_with(mock_return_value, CLIENT_ADDRESS)

        assert handler.port == PORT

    def test_handle_all_value(self, mocket, server):
        """Test the handle method"""
        return
        request = b'dummy_request'
        mock_return_value = 'mock return value'

        # mock handle, which is called at instantiate time, inside a try except
        with mock.patch(self.path('handle')):
            handler = PullUDPHandler((request, mocket), CLIENT_ADDRESS, server)

        # Test all values case
        with mock.patch(self.path('_single_value')) as _single_value:
            with mock.patch(self.path('_all_values')) as _all_values:
                _all_values.return_value = mock_return_value
                handler.handle()
                _all_values.assert_called_once_with(request)
                assert not _single_value.called
                mocket.sendto.assert_called_once_with(mock_return_value, CLIENT_ADDRESS)
