""" Small module to handle sql inserts """

import threading
import MySQLdb
import time

class SqlSaver(threading.Thread):
    """ Common class for putting stuff in databases """
    def __init__(self, queue, username):
        threading.Thread.__init__(self)
        self.daemon = True
        self.queue = queue
        self.cnxn = MySQLdb.connect(host="servcinf",
                                    user=username,
                                    passwd=username,
                                    db="cinfdata")
        self.cursor = self.cnxn.cursor()
        self.commits = 0
        self.commit_time = 0
        
    def run(self):
        while True:
            start = time.time()
            query = self.queue.get()
            self.cursor.execute(query)
            self.cnxn.commit()
            self.commits += 1
            self.commit_time = time.time() - start
        self.cnxn.close()
