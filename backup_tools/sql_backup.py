import os
import gzip
import json
import time
import pathlib
import argparse
import datetime
from subprocess import Popen, PIPE

from PyExpLabSys.common.utilities import get_logger

import pymysql

print(os.environ)
print()

EXPORT_PATH = os.environ.get('PYEXPLABSYS_EXPORT_PATH')
HOST = os.environ.get('PYEXPLABSYS_HOST')
USER = os.environ.get('PYEXPLABSYS_USER')
PASSWD = os.environ.get('PYEXPLABSYS_PASSWD')
DB = os.environ.get('PYEXPLABSYS_DB')

print(DB)
print(EXPORT_PATH)


LOGGER = get_logger(
    'SQL backup',
    level='info',
    file_log=True,
    file_name='sql_backup.log',
    terminal_log=False,
)


# TODO:
# It is the intention that this software can perform both a full and a differential
# backup so far only full backups are implemented
class PyExpLabSysBackup:
    def __init__(self, backup_path, differential=False):
        # Todo - so far only full backups are implemented
        assert differential is False

        if not backup_path.is_dir():
            print('Invalid backup path: {}'.format(backup_path))

        self.differential = differential
        isotime = datetime.datetime.now().isoformat(timespec='seconds')
        LOGGER.info('Starting backup on {}'.format(isotime))
        self.conn = pymysql.connect(host=HOST, user=USER, passwd=PASSWD, db=DB)
        self.cursor = self.conn.cursor()
        self.untreated_tables = self._find_all_tables()
        self.backed_up_tables = []
        if differential:
            self.path = backup_path / (isotime + '_diff')
        else:
            self.path = backup_path / (isotime + '_complete')
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
        msg = 'Backing up all dateplots since beginning of time'
        LOGGER.info(msg)
        print(msg)
        untreated_tables = self.untreated_tables.copy()
        for table in untreated_tables:
            if table == 'dateplots_descriptions':
                # Dateplots descriptions is not a dateplot table and
                # wil go in the miscellaneous category.
                continue
            if 'dateplot' in table:
                stats = self.perform_backup(table, [table])
                self.stats['dateplots'][table] = stats
        msg = 'Backup of dateplots done in {:.0f}s'.format(time.time() - t)
        print(msg)
        LOGGER.info(msg)

    def backup_measurements(self):
        t = time.time()
        msg = 'Backing up all xy-measurements since beginning of time'
        print(msg)
        LOGGER.info(msg)
        # Backing up all related measurements - dateplots are also found
        # by this algorithm, but will typically be removed from
        # untreated_tables by the backup_dateplots function
        untreated_tables = self.untreated_tables.copy()
        for table in untreated_tables:
            if 'measurements' in table:
                name = table[table.find('_'):]
                tables = self.find_matching_tables(name)
                stats = self.perform_backup(table, tables)
                self.stats['measurements'][name] = stats
        msg = 'Backup of measurements done in {:.0f}s'.format(time.time() - t)
        print(msg)
        LOGGER.info(msg)

    def backup_misc_tables(self):
        t = time.time()
        msg = 'Backing up all tables that has so far not been backed up'
        print(msg)
        LOGGER.info(msg)
        untreated_tables = self.untreated_tables.copy()
        stats = self.perform_backup('misc', untreated_tables)
        self.stats['misc'] = stats
        msg = 'Backup of misc done in {:.0f}s'.format(time.time() - t)
        print(msg)
        LOGGER.info(msg)

    def backup_users(self):
        # reader needs full access to read this:
        # grant select on *.* to `reader`@`%`;
        cmd = 'mysqldump --single-transaction --system=users --insert-ignore --all-databases --no-data --host={} --user={} --password={}'
        cmd = cmd.format(HOST, USER, PASSWD, DB)
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        with gzip.open(self.path / 'metadata.sql.gz', "wb") as f:
            f.writelines(p.stdout)

    def perform_backup(self, name, table_list):
        t = time.time()
        filename = '{}.sql.gz'.format(name)
        LOGGER.info('Backing up: {} as {}'.format(table_list, filename))
        # https://stackoverflow.com/questions/3600948/python-subprocess-mysqldump-and-pipes
        # Add, --insert-ignore to ensure partial backups can be imported even a few
        # rows are overlapping
        # --no-create-info to not need DROP TABLE grant for reader. The tables
        # will be created as part of the initialization along with the users.
        cmd = 'mysqldump --single-transaction --no-create-info --insert-ignore --host={} --user={} --password={} {}'
        cmd = cmd.format(HOST, USER, PASSWD, DB)

        # Holds max-id and number of rows for each table
        table_stats = {}
        for table in table_list:
            status_query = 'select max(id), count(*) from `{}` where id > 0'.format(
                table
            )
            self.cursor.execute(status_query)
            max_id, count = list(self.cursor.fetchall())[0]
            table_stats[table] = {'max_id': max_id, 'count': count}
            self.untreated_tables.remove(table)
            self.backed_up_tables.append(table)
            cmd += ' ' + table

        # We do not enforce table-locking between the select statements and the
        # dump-command, however, in practice only a few miliseconds will separate
        # the two commands - the error will be very small and always with the stats
        # being either correct or sligltly too low. Subsequent backups will be
        # either perfectly aligen or slightly overlapping which is not a problem
        # due to --insert-ignore.
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        backup_file = self.path / filename
        with gzip.open(self.path / filename, "wb") as f:
            f.writelines(p.stdout)
        t_total = time.time() - t
        stats = {
            'cmd': cmd,
            'tables': table_list,
            'table_stats': table_stats,
            'time': t_total,
            'size': backup_file.stat().st_size,
            'where_clause': '',  # TODO!
        }
        LOGGER.info('Done in {:.1f}s'.format(t_total))
        return stats


def main():
    def dir_path(path):
        os_path = pathlib.Path(path).expanduser()
        if os_path.is_dir():
            return os_path
        else:
            raise argparse.ArgumentTypeError('{} is not a valid path'.format(path))

    parser = argparse.ArgumentParser(
        description='Tool for backing up PyExpLabSys sql-data'
    )

    parser.add_argument('--path', type=dir_path)
    parser.add_argument('--version', action='store_true')
    args = vars(parser.parse_args())

    if args['version']:
        print('SQL Export version 1.0')
        exit()

    path = args['path']
    if not path:
        path_raw = EXPORT_PATH
        path = dir_path(path_raw)

    if not path:
        exit('No export path on either command line og env-variable')

    PB = PyExpLabSysBackup(path)
    PB.backup_users()
    PB.backup_dateplots()
    PB.backup_measurements()
    PB.backup_misc_tables()
    PB.write_stats()
    print('Untreated tables:')
    print(PB.untreated_tables)


if __name__ == '__main__':
    # export PYEXPLABSYS_EXPORT='~/Backups/cinfdatabackup'
    main()
