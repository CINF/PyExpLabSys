# pylint: disable=too-many-arguments

"""This module contains modules for saving data to a database"""


from __future__ import unicode_literals, division, print_function
import logging
import re
from collections import namedtuple
import PyExpLabSys.common.sql_saver as sql_saver_module


# Used for check of valid, un-escaped column names, to prevent injection
COLUMN_NAME = re.compile(r'^[0-9a-zA-Z$_]*$')

# namedtuple used for custom column formatting, see MeasurementSaver.__init__
CustomColumn = namedtuple('CustomColumn', ['value', 'format_string'])

MEASUREMENT_SAVER_LOG = logging.getLogger(__name__ + '.MeasurementSaver')
MEASUREMENT_SAVER_LOG.addHandler(logging.NullHandler())


class MeasurementSaver(object):
    """A class to save a measurement"""

    host = 'servcinf'
    database = 'cinfdata'

    def __init__(self, measurements_table, xy_values_table, username, password,
                 measurement_specs=None):
        """Initialize local parameters

        Args:
            measurements_table (str): The name of the measurements table
            xy_values_table (str): The name of the xy values table
            username (str): The database username
            passwork (str): The database password
            measurement_specs (sequence): A sequence of ``measurement_codename,
                metadata`` pairs, see below

        ``measurement_specs`` is used if you want to initialize all the measurements at
        ``__init__`` time. You can also do it later with :meth:`add_measurement`. The
        expected value is a sequence of ``measurement_codename, metadata`` e.g::

            measurement_specs = [
                ['M2', {'type': 5, 'timestep': 0.1, 'mass_label': 'M2M'}],
                ['M28', {'type': 5, 'timestep': 0.1, 'mass_label': 'M2M'}],
                ['M32', {'type': 5, 'timestep': 0.1, 'mass_label': 'M2M'}],
            ]

        As above, the expected ``metadata`` is simply a mapping of column names to column
        values in the ``measurements_table``.

        Per default, the value will be put into the table as is. If it is necessary to do
        SQL processing on the value, to make it fit the column type, then the value must
        be replaced with a :class:`CustomColumn` instance, whose arguments are the value
        and the format/processing string. The format/processing string must contain a '%s'
        as a placeholder for the value. It could look like this::

            measurement_specs = [
                ['M2', {'type': 5, 'time': CustomColumn(M2_timestamp, 'FROM_UNIXTIME(%s)')}],
                ['M28', {'type': 5, 'time': CustomColumn(M28_timestamp, 'FROM_UNIXTIME(%s)')}],
            ]

        The most common use for this is the one shown above, where the ``time`` column is
        of type timestamp and the time value (e.g. in M2_timestamp) is a unix
        timestamp. The unix timestamp is converted to a SQL timestamp with the
        ``FROM_UNIXTIME`` SQL function.

        .. note:: The SQL timestamp column understand the :py:class:`datetime.datetime`
            type directly, so if the input timestamp is already on that form, then there
            is no need to convert it

        """
        MEASUREMENT_SAVER_LOG.info(
            '__init__ with measurement_table=%s, xy_values_table=%s, '
            'username=%s, password=*****, measurement_specs: %s',
            measurements_table, xy_values_table, username, measurement_specs,
        )

        # Initialize instance variables
        self.measurements_table = measurements_table
        self.xy_values_table = xy_values_table
        self.sql_saver = sql_saver_module.SqlSaver(username, password)
        self.sql_saver.start()

        # Initialize queries
        self.insert_measurement_query = 'INSERT INTO {} ({{}}) values ({{}})'\
            .format(measurements_table)
        self.insert_point_query = 'INSERT INTO {} (measurement, x, y) values (%s, %s, %s)'\
            .format(xy_values_table)
        self.insert_batch_query = 'INSERT INTO {} (measurement, x, y) values {{}}'\
            .format(xy_values_table)

        # Initialize measurement ids
        self.measurement_ids = {}
        if measurement_specs:
            for codename, metadata_dict in measurement_specs:
                self.add_measurement(codename, metadata_dict)

    def add_measurement(self, codename, metadata):
        """Add a measurement

        This is equivalent to forming the entry in the measurements table with the
        metadata values and saving the id of this entry locally for use with
        :meth:`add_point`.

        Args:
            codename (str): The codename that this measurement should have
            metadata (dict): The dictionary that holds the information for the
                measurements table. See :meth:`__init__` for details.
        """
        MEASUREMENT_SAVER_LOG.info('Add measurement codenamed: \'%s\' with metadata: %s',
                                   codename, metadata)
        # Collect column names, values and format strings, a format string is a SQL value
        # placeholder including processing like e.g: %s or FROM_UNIXTIME(%s)
        column_names, values, value_format_strings = [], [], []
        for column_name, value in metadata.items():
            if not COLUMN_NAME.match(column_name):
                message = 'Invalid column name: \'{}\'. Only column names using a-z, '\
                          'A-Z, 0-9 and \'_\' and \'$\' are allowed'.format(column_name)
                raise ValueError(message)

            if isinstance(value, CustomColumn):
                # If the value from the metadata dict is a CustomColumn (which is 2 value
                # tuple), the unpack it
                real_value, value_format_string = value
            else:
                # Else, that value is just a value with default place holder
                real_value, value_format_string = value, '%s'

            column_names.append(column_name)
            values.append(real_value)
            value_format_strings.append(value_format_string)

        # Form the column string e.g: 'name, time, type'
        column_string = ', '.join(column_names)
        # Form the value marker string e.g: '%s, FROM_UNIXTIME(%s), %s'
        value_marker_string = ', '.join(value_format_strings)
        query = self.insert_measurement_query.format(column_string, value_marker_string)

        # Make the insert and save the measurement_table id for use in saving the data
        cursor = self.sql_saver.cnxn.cursor()
        cursor.execute(query, values)
        self.measurement_ids[codename] = cursor.lastrowid
        cursor.close()
        MEASUREMENT_SAVER_LOG.debug('Measurement codenamed: \'%s\' added', codename)

    def save_point(self, codename, point):
        """Save a point for a specific codename

        Args:
            codename (str): The codename for the measurement to add the point to
            point (sequence): A sequence of x, y
        """
        MEASUREMENT_SAVER_LOG.debug('For codename \'%s\' save point: %s', codename, point)
        try:
            query_args = [self.measurement_ids[codename]]
        except KeyError:
            message = 'No entry in measurements_ids for codename: \'{}\''.format(codename)
            raise ValueError(message)

        # The query expects 3 values; measurement_id, x, y
        query_args.extend(point)
        self.sql_saver.enqueue_query(self.insert_point_query, query_args)

    def save_points_batch(self, codename, x_values, y_values, batchsize=100):
        """Save a number points for the same codename in batches

        Args:
            codename (str): The codename for the measurement to save the points for
            x_values (sequence): A sequence of x values
            y_values (sequence): A sequence of y values
            batchsize (int): The number of points to send in the same batch
        """
        MEASUREMENT_SAVER_LOG.debug('For codename \'%s\' save %s points in batches of %s',
                                    codename, len(x_values), batchsize)

        # Check lengths and get measurement_id
        if len(x_values) != len(y_values):
            raise ValueError('Number of x and y values must be the same. Values are {} and {}'\
                             .format(len(x_values), len(y_values)))
        try:
            measurement_id = self.measurement_ids[codename]
        except KeyError:
            message = 'No entry in measurements_ids for codename: \'{}\''.format(codename)
            raise ValueError(message)

        # Gather values in batches of batsize, start enumerate from 1, to make the criteria
        values = []
        number_of_values = 0
        for x_value, y_value in zip(x_values, y_values):
            # Add this point
            values.extend([measurement_id, x_value, y_value])
            number_of_values += 1

            # Save a batch (> should not be necessary)
            if number_of_values >= batchsize:
                value_marker_string = ', '.join(['(%s, %s, %s)'] * number_of_values)
                query = self.insert_batch_query.format(value_marker_string)
                self.sql_saver.enqueue_query(query, values)
                values = []
                number_of_values = 0

        # Save the remaining number of points (smaller than the batchsize)
        if number_of_values > 0:
            value_marker_string = ', '.join(['(%s, %s, %s)'] * number_of_values)
            query = self.insert_batch_query.format(value_marker_string)
            self.sql_saver.enqueue_query(query, values)

    def stop(self):
        """Stop the MeasurementSaver

        And shut down the underlying :class:`PyExpLabSys.common.sql_saver.SqlSaver`
        instance nicely.
        """
        MEASUREMENT_SAVER_LOG.info('stop called')
        self.sql_saver.stop()
        MEASUREMENT_SAVER_LOG.debug('stopped')

    @property
    def connection(self):
        """Return the connection of the underlying SqlSaver instance"""
        return self.sql_saver.cnxn
