# pylint: disable=no-member,no-self-use,too-many-locals
"""Functional test of the database_saver module up against the real database

NOTE: This test will write values to the dateplots_dummy table.
"""

import time
import math
import mock
import pytest
import numpy as np
import MySQLdb
from PyExpLabSys.common.database_saver import DataSetSaver, ContinuousDataSaver


CONNECTION = MySQLdb.connect(host='servcinf', user='cinf_reader',
                             passwd='cinf_reader', db='cinfdata')
CURSOR = CONNECTION.cursor()

### DataSetSaver
class TestDataSetSaver(object):
    """Test the DataSetSaver class"""

    # Keep this number divisible by 10
    number_of_points = 500
    batch_good = 50
    batch_bad = 51

    @pytest.fixture(scope='class')
    def data_for_tests(self):
        """Generate test data

        Returns:
            tuple: codenames, metadata_sets, x_values, y0_values, y1_values
        """
        # Form test data (sine to time)
        start = time.time()
        x_values = np.linspace(0, 10, self.number_of_points)
        y0_values = np.sin(start + x_values)
        y1_values = np.sin(start + np.pi + x_values)
        return x_values, y0_values, y1_values

    @pytest.fixture(scope='class')
    def metadata_for_tests(self):
        """Generate metadata for tests

        Returns:
            tuple: codenames, metadata_sets
        """
        # Codenames and metadata for two data sets
        codenames = ('sine_to_time', 'sine_to_time_plus_pi')
        metadata_sets = (
                {'type': 47, 'comment': 'sine', 'timestep': 10, 'pass_energy': 123.4},
                {'type': 47, 'comment': 'shifted sine', 'timestep': -1, 'pass_energy': 987.6}
            )
        return codenames, metadata_sets

    @pytest.yield_fixture(scope='function')
    def db_saver(self):
        """Autoclosing db_saver yield_fixture"""
        # Init db_saver
        db_saver = DataSetSaver('measurements_dummy', 'xy_values_dummy', 'dummy', 'dummy')
        db_saver.start()
        yield db_saver
        db_saver.stop()

    def test_save_point(self, db_saver, data_for_tests, metadata_for_tests):
        """Test the save_point method"""
        # Unpack data and metadata
        x_values, y0_values, y1_values = data_for_tests
        codenames, metadata_sets = metadata_for_tests

        # Add the measurements
        for codename, metadata in zip(codenames, metadata_sets):
            db_saver.add_measurement(codename, metadata)

        # Save the test data
        for x_value, y0_value, y1_value in zip(x_values, y0_values, y1_values):
            db_saver.save_point('sine_to_time', (x_value, y0_value))
            db_saver.save_point('sine_to_time_plus_pi', (x_value, y1_value))

        # Make sure the queue has emptied
        while db_saver.sql_saver.queue.qsize() > 0:
            time.sleep(0.01)

        # Check if the data got there
        query = 'SELECT x, y from xy_values_dummy WHERE measurement={} ORDER BY id asc'
        for codename, y_values in zip(codenames, (y0_values, y1_values)):
            CURSOR.execute(query.format(db_saver.measurement_ids[codename]))
            data = np.array(CURSOR.fetchall())
            assert data.shape == (self.number_of_points, 2)
            assert np.allclose(x_values, data[:, 0])
            assert np.allclose(y_values, data[:, 1])

    @pytest.mark.parametrize("batchsize", (batch_good, batch_bad),
                             ids=['does not fit batches', 'fits batches'])
    def test_save_points_batch(self, db_saver, data_for_tests, metadata_for_tests, batchsize):
        """Test the save_points_batch method"""
        # Unpack data and metadata
        x_values, y0_values, y1_values = data_for_tests
        codenames, metadata_sets = metadata_for_tests

        # Add the measurements
        for codename, metadata in zip(codenames, metadata_sets):
            db_saver.add_measurement(codename, metadata)

        # Save the test data
        db_saver.save_points_batch('sine_to_time', x_values, y0_values,
                                   batchsize=batchsize)
        db_saver.save_points_batch('sine_to_time_plus_pi', x_values, y1_values,
                                   batchsize=batchsize)

        # Make sure the queue has emptied
        while db_saver.sql_saver.queue.qsize() > 0:
            time.sleep(0.01)

        # Check if the data got there
        query = 'SELECT x, y from xy_values_dummy WHERE measurement={} ORDER BY id asc'
        for codename, y_values in zip(codenames, (y0_values, y1_values)):
            CURSOR.execute(query.format(db_saver.measurement_ids[codename]))
            data = np.array(CURSOR.fetchall())
            assert data.shape == (self.number_of_points, 2)
            assert np.allclose(x_values, data[:, 0])
            assert np.allclose(y_values, data[:, 1])


class TestContinuousDataSaver(object):
    """Test the ContinuousDataSaver class"""

    def test_save_point_now(self):
        """Test the continous logger by sending data without timestamps"""
        # The save_point_now method uses time.time to get a unix timestamp to attach. However,
        # since points are only saved with a seconds precision, testing multiple points would
        # take multiple seconds. To avoid this, we mock all the calls to time.
        number_of_points = 10
        start = time.time() - number_of_points
        # Form times 1 second apart from 100 seconds ago
        times = [start + increment for increment in range(number_of_points)]
        # For return values of time, we need each of them twice, because we store two datasets
        double_times = []
        for increment in range(number_of_points):
            double_times.append(start + increment)
            double_times.append(start + increment)

        # Init lists for local storage of the data
        data1 = []
        data2 = []

        # Init continuous database saver
        db_saver = ContinuousDataSaver('dateplots_dummy', 'dummy', 'dummy',
                                       ['dummy_sine_one', 'dummy_sine_two'])
        db_saver.start()

        def mytime():
            """Replacement function for time"""
            return double_times.pop(0)

        with mock.patch('time.time') as mock_time:
            mock_time.side_effect = mytime
            for now in times:
                # The data points are just sines to the unix timestamp
                value = math.sin(now)
                data1.append([now, value])
                db_saver.save_point_now('dummy_sine_one', value)

                value = math.sin(now + math.pi)
                data2.append([now, value])
                db_saver.save_point_now('dummy_sine_two', value)
            assert mock_time.call_count == number_of_points * 2

        # Make sure all points have been saved
        while db_saver.sql_saver.queue.qsize() > 0:
            time.sleep(0.01)

        # Get the measurement code numbers from the saver
        codes = (db_saver.codename_translation['dummy_sine_one'],
                 db_saver.codename_translation['dummy_sine_two'])

        # Check if the data has been properly written to the db
        for data, code in zip((data1, data2), codes):
            # Get the last number_of_points points for this code
            query = 'SELECT UNIX_TIMESTAMP(time), value FROM dateplots_dummy '\
                    'WHERE type={} ORDER BY id DESC LIMIT {}'\
                    .format(code, number_of_points)
            CURSOR.execute(query)
            # Reverse the points to get oldest first
            fetched = reversed(CURSOR.fetchall())
            for point_original, point_control in zip(data, fetched):
                # Times are rounded to integers, so it should just be a difference
                # of less than ~0.51 seconds
                assert np.isclose(point_original[0], point_control[0], atol=0.51)
                assert np.isclose(point_original[1], point_control[1])

        db_saver.stop()


    def test_enqueue_point(self):
        """Test the continous logger by sending data with timestamps"""
        # Make timestamps to use
        number_of_points = 10
        start = time.time()
        times = [start + increment for increment in range(number_of_points)]

        # Form the lists for local storage of data, for tests
        data1 = []
        data2 = []

        # Init the db_saver
        db_saver = ContinuousDataSaver('dateplots_dummy', 'dummy', 'dummy',
                                       ['dummy_sine_one', 'dummy_sine_two'])
        db_saver.start()

        # Save the points
        for now in times:
            value = math.sin(now)
            data1.append([now, value])
            db_saver.save_point('dummy_sine_one', (now, value))
            value = math.sin(now + math.pi)
            data2.append([now, value])
            db_saver.save_point('dummy_sine_two', (now, value))

        # Make sure the queue has been cleared
        while db_saver.sql_saver.queue.qsize() > 0:
            time.sleep(0.01)

        # Get the measurement code numbers from the logger
        codes = (db_saver.codename_translation['dummy_sine_one'],
                 db_saver.codename_translation['dummy_sine_two'])

        # Check if the data has been properly written to the db
        for data, code in zip((data1, data2), codes):
            query = 'SELECT UNIX_TIMESTAMP(time), value FROM dateplots_dummy '\
                'WHERE type={} ORDER BY id DESC LIMIT {}'\
                    .format(code, number_of_points)
            CURSOR.execute(query)
            fetched = reversed(CURSOR.fetchall())
            for point_original, point_control in zip(data, fetched):
                # Time is rounded, so it is only correct to within ~0.51 s
                assert np.isclose(point_original[0], point_control[0], atol=0.51)
                assert np.isclose(point_original[1], point_control[1])

        db_saver.stop()
