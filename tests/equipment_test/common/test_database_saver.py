# pylint: disable=W0212
"""Module to test the general continous loggers.

When executed with pytest, the test functions in this module will test both
the enqueue_point_now and enqueue_point functions, by saving the values,
reading them back from the database and comparing.

NOTE: This test will write values to the dateplots_dummy table.
"""

import time
import math
import mock
from PyExpLabSys.common.database_saver import DataSetSaver, ContinuousDataSaver


### DataSetSaver



def test_enqueue_point_now():
    """Test the continous logger by sending data without timestamps"""

    # Lists to store the data locally
    number_of_points = 100
    start = time.time() - number_of_points
    times = []
    for increment in range(number_of_points):
        times.append(start + increment)
        times.append(start + increment)
    data1 = []
    data2 = []

    def mytime():
        return times.pop(0)

    with mock.patch('time.time') as mock_time:
        db_saver = ContinuousDataSaver('dateplots_dummy', 'dummy', 'dummy',
                                       ['dummy_sine_one', 'dummy_sine_two'])
        db_saver.start()

        mock_time.side_effect = mytime
        for now in times:
            # The data points are just sines to the unix timestamp
            value = math.sin(now)
            data1.append([now, value])
            db_saver.save_point_now('dummy_sine_one', value)

            value = math.sin(now + math.pi)
            data2.append([now, value])
            db_saver.save_point_now('dummy_sine_two', value)
        print("##", mock_time.call_count)

    while db_saver.sql_saver.queue.qsize() > 0:
        time.sleep(0.01)

    # Get the measurement code numbers from the logger (really should be
    # tested on its own)
    codes = (db_saver.codename_translation['dummy_sine_one'],
             db_saver.codename_translation['dummy_sine_two'])

    # Check if the data has been properly written to the db
    cursor = db_saver.connection.cursor()
    for data, code in zip((data1, data2), codes):
        # Select date newer than 1 seconds less than the oldest time in data
        time_start = min([element[0] for element in data]) - 1
        print(code)
        query = 'SELECT UNIX_TIMESTAMP(time), value FROM dateplots_dummy '\
                'WHERE type={} ORDER BY id DESC LIMIT {}'\
                .format(code, number_of_points)
        cursor.execute(query)
        fetched = cursor.fetchall()
        for point_original, point_control in zip(data, fetched):
            # Times are rounded to integers, so it should just be a difference
            # of less than ~0.5 second
            assert(abs(point_original[0]-point_control[0]) < 0.51)
            assert(abs(point_original[1]-point_control[1]) < 1E-12)


    db_saver.stop()


def gggtest_enqueue_point():
    """Test the continous logger by sending data with timestamps"""
    db_saver = ContinuousDataSaver('dateplots_dummy', 'dummy', 'dummy',
                                   ['dummy_sine_one', 'dummy_sine_two'])
    db_saver.start()
    # Lists to store the data locally
    data1 = []
    data2 = []
    for _ in range(10):
        time.sleep(0.01)
        time_ = time.time()
        point = math.sin(time_)
        data1.append([time_, point])
        db_saver.save_point('dummy_sine_one', (time_, point))
        time_ = time.time()
        point = math.sin(time_ + math.pi)
        data2.append([time_, point])
        db_saver.save_point('dummy_sine_two', (time_, point))

    # Make sure the queue has been cleared
    while db_saver.sql_saver.queue.qsize() > 0:
        time.sleep(0.01)

    # Get the measurement code numbers from the logger (really should be
    # tested on its own)
    codes = (db_saver.codename_translation['dummy_sine_one'],
             db_saver.codename_translation['dummy_sine_two'])

    # Check if the data has been properly written to the db
    cursor = db_saver.connection.cursor()
    for data, code in zip((data1, data2), codes):
        time_start = min([element[0] for element in data]) - 1
        query = 'SELECT UNIX_TIMESTAMP(time), value FROM dateplots_dummy '\
            'WHERE time > FROM_UNIXTIME({}) and type={}'\
                .format(time_start, code)
        cursor.execute(query)
        fetched = cursor.fetchall()
        for point_original, point_control in zip(data, fetched):
            # Time is rounded, so it is only correct to within ~0.5 s
            assert(abs(point_original[0]-point_control[0]) < 0.51)
            assert(abs(point_original[1]-point_control[1]) < 1E-12)
    cursor.close()

    db_saver.stop()
