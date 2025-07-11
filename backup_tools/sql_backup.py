import gzip
import time
import pathlib
import datetime

from subprocess import Popen, PIPE

import pymysql

HOST = '10.11.114.11'
USER = 'reader'
PASSWD = 'reader'
DB = 'nanomadedata'


class PyExpLabSysBackup:
    def __init__(self):
        self.conn = pymysql.connect(host=HOST, user=USER, passwd=PASSWD, db=DB)
        self.cursor = self.conn.cursor()
        self.untreated_tables = self._find_all_tables()
        self.backed_up_tables = []
        isotime = datetime.datetime.now().isoformat(timespec='seconds')
        self.path = pathlib.Path.cwd() / isotime
        self.path.mkdir()

    def _find_all_tables(self):
        query = 'show tables;'
        self.cursor.execute(query)
        tables_raw = list(self.cursor.fetchall())
        tables = []
        for table in tables_raw:
            tables.append(table[0])
        return tables

    def find_matching_tables(self, name):
        matching = []
        for table in self.untreated_tables:
            if name in table:
                matching.append(table)
        return matching

    def find_dateplots(self):
        t = time.time()
        print('Backing up all dateplots since beginning of time')
        untreated_tables = self.untreated_tables.copy()
        for table in untreated_tables:
            if table == 'dateplots_descriptions':
                # Dateplots descriptions is not a dateplot table and
                # wil go in the miscellaneous category.
                continue
            if 'dateplot' in table:
                self.perform_backup(table, [table])
                self.untreated_tables.remove(table)
                self.backed_up_tables.append(table)
        print('Done in {:.0f}s'.format(time.time() - t))

    def perform_backup(self, name, table_list):
        t = time.time()
        filename = '{}.sql.gz'.format(name)
        print('Backing up: {} as {}'.format(table_list, filename))
        # https://stackoverflow.com/questions/3600948/python-subprocess-mysqldump-and-pipes
        cmd = 'mysqldump --single-transaction --host={} --user={} --password={} {}'
        cmd = cmd.format(HOST, USER, PASSWD, DB)
        for table in table_list:
            cmd += ' ' + table

        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        # with gzip.open(path, "wb") as f:
        #     f.writelines(p.stdout)
        with gzip.open(self.path / filename, "wb") as f:
            f.writelines(p.stdout)
        print('Done in {:.1f}s'.format(time.time() - t))


if __name__ == '__main__':
    PB = PyExpLabSysBackup()
    PB.find_dateplots()

    # t = time.time()
    # # name = 'linkam'
    # name = 'cryostat'
    # tables = PB.find_matching_tables(name)
    # print('Backup {}'.format(name))
    # PB.perform_backup(name, tables)
    # print('Backup done - {:.0f}s'.format(time.time() - t))

    # print()

    print('Untreated tables:')
    print(PB.untreated_tables)
    print()
    print('Backed-up_tables')
    print(PB.backed_up_tables)


# query = 'SELECT x*1000000, y FROM ' + XY_VALUES_TABLE
# query += ' where measurement = ' + str(spectrum_number)
