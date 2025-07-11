import gzip
import json
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
        self.t_start = time.time()
        self.stats = {
            'dateplots': {},
            'measurements': {},
            'misc': {},
            'stats': {'start': datetime.datetime.now().isoformat()},
        }

    def _find_all_tables(self):
        query = 'show tables;'
        self.cursor.execute(query)
        tables_raw = list(self.cursor.fetchall())
        tables = []
        for table in tables_raw:
            tables.append(table[0])
        return tables

    def write_stats(self):
        self.stats['stats']['end'] = datetime.datetime.now().isoformat()
        self.stats['stats']['total_time'] = time.time() - self.t_start
        filename = self.path / 'stats.json'
        with filename.open("w", encoding="UTF-8") as stat_file:
            json.dump(self.stats, stat_file)

    def find_matching_tables(self, name):
        matching = []
        for table in self.untreated_tables:
            if name in table:
                matching.append(table)
        return matching

    def backup_dateplots(self):
        t = time.time()
        print('Backing up all dateplots since beginning of time')
        untreated_tables = self.untreated_tables.copy()
        for table in untreated_tables:
            if table == 'dateplots_descriptions':
                # Dateplots descriptions is not a dateplot table and
                # wil go in the miscellaneous category.
                continue
            if 'dateplot' in table:
                stats = self.perform_backup(table, [table])
                self.untreated_tables.remove(table)
                self.backed_up_tables.append(table)
                self.stats['dateplots'][table] = stats
        print('Done in {:.0f}s'.format(time.time() - t))

    def backup_measurements(self):
        t = time.time()
        print('Backing up all xy-measurements since beginning of time')
        # Backing up all related measurements - dateplots are also found
        # by this algorithm, but will typically be removed from
        # untreated_tables by the backup_dateplots function
        untreated_tables = self.untreated_tables.copy()
        for table in untreated_tables:
            if 'measurements' in table:
                name = table[table.find('_') :]
                tables = self.find_matching_tables(name)
                stats = self.perform_backup(table, tables)
                self.untreated_tables.remove(table)
                self.backed_up_tables.append(table)
                self.stats['measurements'][name] = stats
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
        backup_file = self.path / filename
        with gzip.open(self.path / filename, "wb") as f:
            f.writelines(p.stdout)
        t_total = time.time() - t
        stats = {
            'cmd': cmd,
            'tables': table_list,
            'time': t_total,
            'size': backup_file.stat().st_size,
            'where_clause': '',  # TODO!
        }
        print('Done in {:.1f}s'.format(t_total))
        return stats


if __name__ == '__main__':
    PB = PyExpLabSysBackup()
    PB.backup_dateplots()
    PB.backup_measurements()
    exit()

    # PB.write_stats()

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
