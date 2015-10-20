# pylint: disable=E1101, E1103
""" Small module to handle sql inserts """

import threading
import MySQLdb
import time

#HOSTNAME = 'servcinf-sql'
HOSTNAME = '127.0.0.1'
DB = 'cinfdata'

class SqlSaver(threading.Thread):
    """ Common class for putting stuff in databases """
    def __init__(self, queue, username):
        threading.Thread.__init__(self)
        self.daemon = True
        self.queue = queue
        self.username = username
        self.cnxn = MySQLdb.connect(host=HOSTNAME, user=username, passwd=username, db=DB)
        self.cursor = self.cnxn.cursor()
        self.commits = 0
        self.commit_time = 0

    def stop(self):
        """ Add stop word to queue to exit the loop when the queue is empty """
        self.queue.put('STOP')
        
    def run(self):
        while True:
            start = time.time()
            query = self.queue.get()
            if query == 'STOP': # Magic key-word to stop Sql Saver
                break
            success = False
            while not success:
                try:
                    self.cursor.execute(query)
                    success = True
                except MySQLdb.OperationalError: # Failed to perfom commit
                    time.sleep(5)
                    try:
                        self.cnxn = MySQLdb.connect(host=HOSTNAME, user=self.username,
                                                    passwd=self.username, db=DB)
                        self.cursor = self.cnxn.cursor()
                    except MySQLdb.OperationalError: # Failed to re-connect
                        pass

            self.cnxn.commit()
            self.commits += 1
            self.commit_time = time.time() - start
        self.cnxn.close()
