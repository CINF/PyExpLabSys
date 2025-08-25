import time
import gzip
import pathlib
import subprocess

from PyExpLabSys.common.utilities import get_logger


HOST = '127.0.0.1'
USER = 'root'
PASSWD = '2dphys'
DB = 'nanomadedata'

LOGGER = get_logger(
    'SQL backup',
    level='info',
    file_log=True,
    file_name='sql_restore.log',
    terminal_log=False,
)


class PyExpLabSysRestore:
    def __init__(self):
        self.path = pathlib.Path.cwd()
        # self.conn = pymysql.connect(host=HOST, user=USER, passwd=PASSWD, db=DB)
        # self.cursor = self.conn.cursor()

    def find_backups(self):
        backups = list(self.path.glob('*'))
        return backups

    def find_backup_components(self, timestamp):
        backups = self.find_backups()
        for backup in backups:
            if timestamp in str(backup):
                break
        backup_path = self.path / backup
        components = backup_path.glob('*')
        file_list = []
        for component in components:
            if 'metadata.sql' in component.name:
                # This is far handled manually
                continue
            if not 'sql.gz' in component.name:
                continue
            file_list.append(component)
        return file_list

    def import_dump(self, dump_file):
        print()
        print('Restoring {}'.format(dump_file))
        # Ideally this would all happen via pumps witout an itermediate file, but
        # this has proven a bit tricky without keeping the entire dump in memory
        print('unzip')
        subprocess.run(['gunzip', dump_file])
        unzipped_file = pathlib.Path(str(dump_file)[:-3])
        print('execute')
        cmd = 'mysql --user=root --password=2dphys nanomadedata <{}'.format(
            unzipped_file
        )
        subprocess.run(cmd, shell=True, text=True)
        print('zip')
        subprocess.run(['gzip', unzipped_file])

    def restore_full_backup(self, timestamp):
        components = self.find_backup_components(timestamp)
        for dump_file in components:
            self.import_dump(dump_file)


if __name__ == '__main__':
    PR = PyExpLabSysRestore()

    # PR.find_backups()

    # PR.restore_full_backup('2025-07-31T14:47:08')
    PR.restore_full_backup('2025-08-25T13:08:57_complete')
