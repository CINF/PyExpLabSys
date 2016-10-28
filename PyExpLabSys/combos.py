"""This module contains socket, database saver and logger heuristic combinations"""

from __future__ import unicode_literals, absolute_import, print_function

from time import time

from .common.sockets import LiveSocket
from .common.database_saver import ContinuousDataSaver


class LiveContinuousLogger(object):
    """A combination of a :class:`.LiveSocket` and a :class:`.ContinuousDataSaver` that also
    does logging heuristics

    FIXME explain the term log

    """

    def __init__(self, name, codenames, continuous_data_table, username, password,
                 time_criteria=None, absolute_criteria=None, relative_criteria=None,
                 live_server_kwargs=None):
        """Initialize local data

        Args:
            name (str): The name to be used in the sockets
            codenames (sequence): A sequence of codenames. These codenames are the
                measurements codenames for the :class:`.ContinuousDataSaver` and they
                will also be used as the codenames for the :class:`.LiveSocket`.
            continuous_data_table (str): The continuous data table to log data to
            username (str): The MySQL username
            password (str): The password for ``username`` in the database
            time_criteria (float or dict): (Optional) The time after which a point will
                always be saved in the database. Either a single value, which will be used
                for all codenames or a dict of codenames to values. If supplying a dict,
                each codename must be present as a key.
            absolute_criteria (float or dict): (Optional) The absolute value difference
                criteria. Either a single value or one for each codename, see
                `time_criteria` for details.
            relative_criteria (float or dict): (Optional) The relative value difference
                criteria. Either a single value or one for each codename, see
                `time_criteria` for details.
            lives_server_kwargs (dict): (Optinal) A dict of keyword arguments for the
                :class:`.LiveSocket`. See the doc string for :meth:`.LiveSocket.__init__`
                for additional details.

        """
        # Initialize local variables
        self.name = name
        self.codenames = set(codenames)  # It should be a set anyway
        
        # Update and check criteria:
        self.time_criteria = self._init_criteria(time_criteria, 'time')
        self.absolute_criteria = self._init_criteria(absolute_criteria, 'absolute')
        self.relative_criteria = self._init_criteria(relative_criteria, 'relative')

        # Init last times and values (non-existing key will trigger save)
        self.last_times = {}
        self.last_values = {}

        # Init live socket and continuous data saver
        if live_server_kwargs is None:
            live_server_kwargs = {}
        self.live_socket = LiveSocket(name, codenames, **live_server_kwargs)
        self.continuous_data_saver = ContinuousDataSaver(
            continuous_data_table, username, password,
            measurement_codenames=codenames,
        )

    def _init_criteria(self, criteria, criteria_name):
        """Init logging criteria to make sure it is either a dictionay with one value for
        each codename or None

        Args:
            criteria (float or dict): Same as in :meth:`.__init__`.
            criteria_name (str): Criteria name ('time', 'absolute' or 'relative')

        Returns:
            dict or None: The dict of criteria or None if criteria in was none
        """
        if criteria is None:
            return None

        # If not a dictionary, assumed to be int or float
        if not isinstance(criteria, dict):
            if not criteria > 0:
                error_message = 'The criterium for {} is expected to be positive. {} is not.'
                raise ValueError(error_message.format(criteria_name, criteria))
            # Return dict with the passed in single value for all keys
            return {codename: criteria for codename in self.codenames}
        else:
            # Check that criteria contains exactly one entry for each codename. Note
            # self.codenames is a set
            if not set(criteria.keys()) == self.codenames:
                error_message = \
                    'There is not a {} criteria in the criteria dict {} for every '\
                    'codename: {}'.format(criteria_name, criteria, self.codenames)
                raise ValueError(error_message)
            return criteria

    def start(self):
        """Start the underlying :class:`.LiveSocket` and :class:`.ContinuousDataSaver`"""
        self.live_socket.start()
        self.continuous_data_saver.start()
        
    def stop(self):
        """Stop the underlying :class:`.LiveSocket` and :class:`.ContinuousDataSaver`"""
        self.live_socket.stop()
        self.continuous_data_saver.stop()

    def log_point_now(self, codename, value):
        """Log a point now

        As the time will be attached the time now.

        For an explanation of what is meant by the term "log", see the
        :class:`class docstring <.LiveContinuousLogger>`.

        Args:
            codename (str): The codename to log this point for
            value (float): The value to store with the time now (:py:func:`time.time`)

        """
        self.log_point(codename, (time(), value))

    def log_point(self, codename, point):
        """Log a point

        For an explanation of what is meant by the term "log", see the
        :class:`class docstring <.LiveContinuousLogger>`.

        Args:
            codename (str): The codename to log this point for
            point (sequence): A (unix_time, value) two item sequence (e.g. list or tuple),
                that represents a point
        """
        self.live_socket.set_point(codename, point)
        if self._test_logging_criteria(codename, point):
            self.continuous_data_saver.save_point(codename, point)
            self._update_last_information(codename, point)

    def log_batch_now(self, values):
        """Log a batch of values now

        For an explanation of what is meant by the term "log", see the
        :class:`class docstring <.LiveContinuousLogger>`.

        Args:
            values (dict): Dict of codenames to values. The values will be stored with the
                time now (:py:func:`time.time`)
        """
        now = time()
        self.log_batch({codename: (now, value) for codename, value in values.items()})

    def log_batch(self, points):
        """Log a batch of points

        For an explanation of what is meant by the term "log", see the
        :class:`class docstring <.LiveContinuousLogger>`.

        Args:
            points (dict): Dict of codenames to points
        """
        self.live_socket.set_batch(points)
        for codename, point in points.items():
            if self._test_logging_criteria(codename, point):
                self.continuous_data_saver.save_point(codename, point)
                self._update_last_information(codename, point)

    def _test_logging_criteria(self, codename, point):
        """Test the logging criteria for a point

        Args:
            codename (str): The codename to log this point for
            point (sequence): A (unix_time, value) two item sequence (e.g. list or tuple),
                that represents a point
        """
        current_time, current_value = point

        # The last values are initialized empty, so always trigger a save on first point
        try:
            last_time = self.last_times[codename]
            last_value = self.last_values[codename]
        except KeyError:
            return True

        # Test time criteria if present
        if self.time_criteria:
            if current_time - last_time > self.time_criteria[codename]:
                return True

        # Test absolute criteria if present
        if self.absolute_criteria:
            if abs(current_value - last_value) > self.absolute_criteria[codename]:
                return True

        # Test relative criteria if present
        if self.relative_criteria:
            try:
                relative_difference = abs(current_value - last_value) / abs(current_value)
            except ZeroDivisionError:
                return True

            if relative_difference > self.absolute_criteria[codename]:
                return True

        return False

        
    def _update_last_information(self, codename, point):
        """Update the information about last logged point"""
        current_time, current_value = point
        self.last_times[codename] = current_time
        self.last_values[codename] = current_value
