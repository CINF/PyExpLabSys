# pylint: disable=W0212
"""Module to test the general continous loggers.

When executed with pytest, the test functions in this module will test both
the enqueue_point_now and enqueue_point functions, by saving the values,
reading them back from the database and comparing.

NOTE: This test will write values to the dateplots_dummy table.
"""

import math
import time
import MySQLdb
from PyExpLabSys.common import loggers

CONNECTION = MySQLdb.connect(host='servcinf',
                             user='dummy',
                             passwd='dummy',
                             db='cinfdata')
CURSOR = CONNECTION.cursor()


def test_enqueue_point_now():
    """Test the continous logger by sending data without timestamps"""
    db_logger = loggers.ContinuousLogger('dateplots_dummy', 'dummy', 'dummy',
                                         ['dummy_sine_one', 'dummy_sine_two'])
    db_logger.start()
    # Lists to store the data locally
    data1 = []
    data2 = []
    for _ in range(3):
        time.sleep(1)
        # The data points are just sines to the unix timestamp
        time_ = time.time()
        point = math.sin(time_)
        data1.append([time_, point])
        db_logger.enqueue_point_now('dummy_sine_one', point)
        time_ = time.time()
        point = math.sin(time_ + math.pi)
        data2.append([time_, point])
        db_logger.enqueue_point_now('dummy_sine_two', point)
    time.sleep(1)
    db_logger.stop()

    # Get the measurement code numbers from the logger (really should be
    # tested on its own)
    codes = (db_logger._codename_translation['dummy_sine_one'],
             db_logger._codename_translation['dummy_sine_two'])

    # Check if the data has been properly written to the db
    for data, code in zip((data1, data2), codes):
        # Select date newer than 1 seconds less than the oldest time in data
        time_start = min([element[0] for element in data]) - 1
        query = 'SELECT UNIX_TIMESTAMP(time), value FROM dateplots_dummy '\
            'WHERE time > FROM_UNIXTIME({}) and type={}'\
                .format(time_start, code)
        CURSOR.execute(query)
        fetched = CURSOR.fetchall()
        for point_original, point_control in zip(data, fetched):
            # Times are rounded to integers, so it should just be a difference
            # of less than ~0.5 second
            assert(abs(point_original[0]-point_control[0]) < 0.51)
            assert(abs(point_original[1]-point_control[1]) < 1E-12)


def test_enqueue_point():
    """Test the continous logger by sending data with timestamps"""
    db_logger = loggers.ContinuousLogger('dateplots_dummy', 'dummy', 'dummy',
                                         ['dummy_sine_one', 'dummy_sine_two'])
    db_logger.start()
    # Lists to store the data locally
    data1 = []
    data2 = []
    for _ in range(3):
        time.sleep(1)
        time_ = time.time()
        point = math.sin(time_)
        data1.append([time_, point])
        db_logger.enqueue_point('dummy_sine_one', (time_, point))
        time_ = time.time()
        point = math.sin(time_ + math.pi)
        data2.append([time_, point])
        db_logger.enqueue_point('dummy_sine_two', (time_, point))
    time.sleep(1)
    db_logger.stop()

    # Get the measurement code numbers from the logger (really should be
    # tested on its own)
    codes = (db_logger._codename_translation['dummy_sine_one'],
             db_logger._codename_translation['dummy_sine_two'])

    # Check if the data has been properly written to the db
    for data, code in zip((data1, data2), codes):
        time_start = min([element[0] for element in data]) - 1
        query = 'SELECT UNIX_TIMESTAMP(time), value FROM dateplots_dummy '\
            'WHERE time > FROM_UNIXTIME({}) and type={}'\
                .format(time_start, code)
        CURSOR.execute(query)
        fetched = CURSOR.fetchall()
        for point_original, point_control in zip(data, fetched):
            # Time is rounded, so it is only correct to within ~0.5 s
            assert(abs(point_original[0]-point_control[0]) < 0.51)
            assert(abs(point_original[1]-point_control[1]) < 1E-12)
