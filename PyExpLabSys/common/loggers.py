# pylint: disable=R0902,R0903,R0913

""" This module contains convinience classes for database logging. The classes
implement queues to contain the data before of loading to the database to
ensure against network or server problems.
"""

import Queue
import threading
import time
import logging
try:
    import MySQLdb
    SQL = 'mysqldb'
    ODBC_PROGRAMMING_ERROR = Exception
except ImportError:
    import pyodbc
    SQL = 'pyodbc'
    ODBC_PROGRAMMING_ERROR = pyodbc.ProgrammingError


LOGGER = logging.getLogger(__name__)
# Make the logger follow the logging setup from the caller
LOGGER.addHandler(logging.NullHandler())


class NoneResponse:
    """NoneResponse"""
    def __init__(self):
        LOGGER.debug('NoneResponse class instantiated')
NONE_RESPONSE = NoneResponse()


class InterruptableThread(threading.Thread):
    """Class to run a MySQL query with a time out"""
    def __init__(self, cursor, query):
        LOGGER.debug('InterruptableThread.__init__ start')
        threading.Thread.__init__(self)
        self.cursor = cursor
        self.query = query
        self.result = NONE_RESPONSE
        self.daemon = True
        LOGGER.debug('InterruptableThread.__init__ end')

    def run(self):
        """Start the thread"""
        LOGGER.debug('InterruptableThread.run start')
        self.cursor.execute(self.query)
        if SQL == 'mysqldb':
            self.result = self.cursor.fetchall()
        else:
            try:
                self.result = self.cursor.fetchall()
            except ODBC_PROGRAMMING_ERROR:
                self.result = None
        LOGGER.debug('InterruptableThread.run end. Executed query: {}'
                     ''.format(self.query))


def timeout_query(cursor, query, timeout_duration=3):
    """Run a mysql query with a timeout

    :param cursor: The database cursor
    :type cursor: MySQL cursor
    :param query: The query to execute
    :type qeury: str
    :param timeout_duration: The timeout duration
    :type timeout_duration: int
    :return: A tuple of results from the query or ``loggers.NONE_RESPONSE`` if
        the query timed out
    """
    LOGGER.debug('timeout_query start')
    # Spawn a thread for the query
    query_thread = InterruptableThread(cursor, query)
    # Start and join
    query_thread.start()
    query_thread.join(timeout_duration)
    LOGGER.debug('timeout_query end')
    return query_thread.result


class StartupException(Exception):
    """Exception raised when the continous logger fails to start up"""
    def __init__(self, *args, **kwargs):
        LOGGER.debug('StartupException instantiated with args, kwargs: {}, {}'
                     ''.format(str(args), str(kwargs)))
        super(StartupException, self).__init__(*args, **kwargs)


class ContinuousLogger(threading.Thread):
    """A logger for continous data as a function of datetime. The class can
    ONLY be used with the new layout of tables for continous data, where there
    is only one table per setup, as apposed to the old layout where there was
    one table per measurement type per setup. The class sends data to the
    ``cinfdata`` database at host ``servcinf``.

    :var host: Database host, value is ``servcinf``.
    :var database: Database name, value is ``cinfdata``.
    """

    host = 'servcinf'
    database = 'cinfdata'

    def __init__(self, table, username, password, measurement_codenames,
                 dequeue_timeout=1, reconnect_waittime=60, dsn=None):
        """Initialize the continous logger

        :param table: The table to log data to
        :type table: str
        :param username: The MySQL username (must have write rights to
            ``table``)
        :type username: str
        :param password: The password for ``user`` in the database
        :type password: str
        :param measurement_codenames: List of measurement codenames that this
            logger will send data to
        :type measurement_codenames: Iterable containing str
        :param dequeue_timeout: The timeout (in seconds) for dequeueing an
            element, which also constitutes the max time to shutdown after the
            thread has been asked to stop. Default is 1.
        :type dequeue_timeout: float or int
        :param reconnect_waittime: Time to wait (in seconds) in between
            attempts to re-connect to the MySQL database, if the connection has
            been lost
        :type reconnect_waittime: float or int
        :raises StartupException: if it is not possible to start the database
            connection or translate the code names
        :param dsn: DSN name of ODBC connection, used on Windows only
        :type dsn: str
        """
        LOGGER.info('CL: __init__ called')
        # Initialize thread
        super(ContinuousLogger, self).__init__()
        self.daemon = True
        self._stop = False
        LOGGER.debug('CL: thread initialized')
        # Initialize local variables
        self.mysql = {'table': table, 'username': username,
                      'password': password,
                      'dsn': dsn}
        self._dequeue_timeout = dequeue_timeout
        self._reconnect_waittime = reconnect_waittime
        self._cursor = None
        self._connection = None
        self.data_queue = Queue.Queue()
        LOGGER.debug('CL: instance attributes initialized')
        # Dict used to translate code_names to measurement numbers
        self._codename_translation = {}
        # Init database connection and get measurement numbers from codenames
        self._init_connection()
        self._init_measurement_numbers(measurement_codenames)
        LOGGER.info('CL: __init__ done')

    def _init_connection(self):
        """Initialize the database connection."""
        try:
            if SQL == 'mysqldb':
                self._connection = MySQLdb.connect(
                    host=self.host, user=self.mysql['username'],
                    passwd=self.mysql['password'], db=self.database
                )
            else:
                connect_string = 'DSN={}'.format(self.mysql['dsn'])
                self._connection = pyodbc.connect(connect_string)
            self._cursor = self._connection.cursor()
            LOGGER.info('CL: Database connection initialized')
        except MySQLdb.OperationalError:
            message = 'Could not connect to database'
            LOGGER.warning('CL: ' + message)
            raise StartupException(message)

    def _init_measurement_numbers(self, measurement_codenames):
        """Get the measurement numbers that corresponds to the measurement
        codenames
        """
        LOGGER.debug('CL: init measurements numbers')
        for codename in measurement_codenames:
            query = 'SELECT id FROM dateplots_descriptions '\
                'WHERE codename=\'{}\''.format(codename)
            self._cursor.execute(query)
            results = self._cursor.fetchall()
            LOGGER.debug('CL: query for {} returned {}'
                         ''.format(codename, str(results)))
            if len(results) != 1:
                message = 'Measurement code name \'{}\' does not have exactly'\
                    ' one entry in dateplots_descriptions'.format(codename)
                LOGGER.critical('CL: ' + message)
                raise StartupException(message)
            self._codename_translation[codename] = results[0][0]
        LOGGER.info('Codenames translated to measurement numbers: {}'
                    ''.format(str(self._codename_translation)))

    def stop(self):
        """Stop the thread"""
        LOGGER.info('CL: Set stop. Wait before returning')
        self._stop = True
        time.sleep(max(1, 1.2 * self._dequeue_timeout))
        LOGGER.debug('CL: Stop finished')

    def run(self):
        """Start the thread. Must be run before points are added."""
        while not self._stop:
            try:
                point = self.data_queue.get(block=True,
                                            timeout=self._dequeue_timeout)
                result = self._send_point(point)
                LOGGER.info('CL: Point "{}" dequeued and sent'.format(point))
                if result is False:
                    self.data_queue.put(point)
                    LOGGER.debug('CL: Point could not be sent. Re-queued')
                    self._reinit_connection()
            except Queue.Empty:
                pass
        # When we stop the logger
        self._connection.close()
        LOGGER.info('Database connection closed. Remaining in queue: {}'
            .format(self.data_queue.qsize()))

    def _send_point(self, point):
        """Send all points in the queue to the data base"""
        result = timeout_query(self._cursor, point)
        LOGGER.debug('CL: timeout_query called from send_point')
        # If the query was un successfully executed, put the points back in
        # the queue and raise and set succes to False
        success = False if (result is NONE_RESPONSE) else True
        return success

    def _reinit_connection(self):
        """Reinitialize the database connection"""
        database_up = False
        while not database_up:
            try:
                LOGGER.debug('CL: Try to re-open database connection')
                self._init_connection()
                database_up = True
            except StartupException:
                pass
            time.sleep(self._reconnect_waittime)
        LOGGER.debug('CL: Database connection re-opened')

    def enqueue_point_now(self, codename, value):
        """Add a point to the queue and use the current time as the time

        :param codename: The measurement codename that this point will be saved
            under
        :type codename: str
        :param value: The value to be logged
        :type value: float
        :return: the Unixtime used
        :rtype: float
        """
        unixtime = time.time()
        LOGGER.debug('CL: Adding timestamp {} to point'.format(unixtime))
        self.enqueue_point(codename, unixtime, value)
        return unixtime

    def enqueue_point(self, codename, unixtime, value):
        """Add a point to the queue

        :param codename: The measurement codename that this point will be saved
            under
        :type codename: str
        :param unixtime: The timestamp for the point
        :type unixtime: float
        :param value: The value to be logged
        :type value: float"""
        meas_number = self._codename_translation[codename]
        query = ('INSERT INTO {} (type, time, value) VALUES '
                 '({}, FROM_UNIXTIME({}), {});')
        query = query.format(self.mysql['table'], meas_number, unixtime, value)
        self.data_queue.put(query)
        LOGGER.info('CL: Point ({}, {}, {}) added to queue. Queue size: {}'
                    ''.format(codename, unixtime, value,
                              self.data_queue.qsize()))
