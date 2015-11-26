# pylint: disable=E1101, E1103

"""Small module to handle SQL inserts

This functionality has been put into its own module, in order to hide away all the
exception handling that makes sure that the module handles loosing its data base
connection without a loss of data.
"""

from __future__ import unicode_literals

import time
import threading
import logging
# Py2/3 import of Queue
try:
    from Queue import Queue
except ImportError:
    from queue import Queue

import MySQLdb


SQL_SAVER_LOG = logging.getLogger(__name__ + '.SqlSaver')
SQL_SAVER_LOG.addHandler(logging.NullHandler())


class SqlSaver(threading.Thread):
    """The SqlSaver class administers a queue from which it makes the SQL inserts

    Attributes:
        queue (Queue.queue): The queue the queries and qeury arguments are stored in. See
            note below.
        commits (int): The number of commits the saver has performed
        commit_time (float): The timespan the last commit took
        cnxn (MySQLdb.connection): The MySQLdb database connection
        cursor (MySQLdb.cursor): The MySQLdb database cursor

    .. note:: In general queries are added to the queue via the
        :meth:enqueue_query`` method. If it is desired to add elements manually, remember
        that they must be on the form of a ``(query, query_args)`` tuple. (These are the
        arguments to the execute method on the cursor object)

    """

    hostname = 'servcinf'
    db = 'cinfdata'

    def __init__(self, username, password, queue=None):
        """Initialize local variables

        Args:
            username (str): The username for the MySQL database
            password (str): The password for the MySQL database
            queue (Queue.queue): A custom queue to use. If it is left out, a new
                :py:class:`Queue.queue` object will be used.
        """

        SQL_SAVER_LOG.info('Init with username: %s, password: ***** and queue: %s',
                           username, queue)
        super(SqlSaver, self).__init__()
        #threading.Thread.__init__(self)
        self.daemon = True

        # Initialize internal variables
        self.username = username
        self.password = password
        self.commits = 0
        self.commit_time = 0

        # Set queue or initialize a new one
        if queue is None:
            self.queue = Queue()
        else:
            self.queue = queue

        # Initialize database connection
        SQL_SAVER_LOG.debug('Open connection to MySQL database')
        self.cnxn = MySQLdb.connect(host=self.hostname, user=username,
                                    passwd=password, db=self.db)
        self.cursor = self.cnxn.cursor()
        SQL_SAVER_LOG.debug('Connection opened, init done')

    def stop(self):
        """Add stop word to queue to exit the loop when the queue is empty"""
        SQL_SAVER_LOG.info('stop called')
        self.queue.put(('STOP', None))
        # Make sure to wait untill it is closed down to return, otherwise we are going to
        # tear down the environment around it
        while self.isAlive():
            time.sleep(10**-5)
        SQL_SAVER_LOG.debug('stopped')

    def enqueue_query(self, query, query_args=None):
        """Enqueue a qeury and arguments

        Args:
            query (str): The SQL query to be executed
            query_args (sequence or mapping): Optional sequence or mapping of arguments
                to be formatted into the query. ``query`` and ``query_args`` in combination
                are the arguments to cursor.execute.
        """
        SQL_SAVER_LOG.debug('Enqueue query \'%s\' with args: %s', query, query_args)
        self.queue.put((query, query_args))
        
    def run(self):
        """Execute SQL inserts from the queue untill stopped"""
        SQL_SAVER_LOG.info('run started')
        while True:
            start = time.time()
            query, args = self.queue.get()
            if query == 'STOP': # Magic key-word to stop Sql Saver
                break
            success = False
            while not success:
                try:
                    self.cursor.execute(query, args=args)
                    success = True
                except MySQLdb.OperationalError: # Failed to perfom commit
                    time.sleep(5)
                    try:
                        self.cnxn = MySQLdb.connect(host=self.hostname, user=self.username,
                                                    passwd=self.password, db=self.db)
                        self.cursor = self.cnxn.cursor()
                    except MySQLdb.OperationalError: # Failed to re-connect
                        pass

            self.cnxn.commit()
            self.commits += 1
            self.commit_time = time.time() - start

        self.cnxn.close()
        SQL_SAVER_LOG.debug('run stopped')
