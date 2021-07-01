"""Module to log the number of pylint errors in PyExpLabSys

To reset statistics e.g. after new pylint version do the following:

As hall user:
#SET SQL_SAFE_UPDATES = 0;
#delete from dateplots_hall where `type` = (select id from dateplots_descriptions where codename = "pylint_errors");
#delete from dateplots_hall where `type` = (select id from dateplots_descriptions where codename = "lines_of_code");
#delete from dateplots_hall where `type` = (select id from dateplots_descriptions where codename = "lines_of_py3_code");

As pylint user:
#truncate pylint;

"""

# --disable=no-member

from __future__ import print_function
import os
import sys
import pickle
import errno
import subprocess
import json
import time
import hashlib
import logging
import logging.handlers
from collections import OrderedDict, Counter
import MySQLdb

from PyExpLabSys.common.supported_versions import python3_only
python3_only(__file__)

# Set this for whether it is running in cron
RUNNING_IN_CRON = os.getenv('CRONTAB') == 'true'

# Configure logging
LOGFILE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'always_lint.log'
)
LOG = logging.getLogger('always_lint')
LOG.setLevel(logging.DEBUG)
ROTATING_FILE_HANDLER = logging.handlers.RotatingFileHandler(
    LOGFILE, maxBytes=10485760, backupCount=10
)
ROTATING_FILE_HANDLER.setLevel(logging.DEBUG)
FORMATTER = logging.Formatter(
    '%(asctime)s:%(name)s: %(levelname)s: %(message)s'
)
ROTATING_FILE_HANDLER.setFormatter(FORMATTER)
TERMINAL_LOGGER = logging.StreamHandler()
if RUNNING_IN_CRON:
    TERMINAL_LOGGER.setLevel(logging.WARNING)
else:
    TERMINAL_LOGGER.setLevel(logging.INFO)
TERMINAL_LOGGER.setFormatter(FORMATTER)
LOG.addHandler(TERMINAL_LOGGER)
LOG.addHandler(ROTATING_FILE_HANDLER)


if sys.version_info.major != 3:
    raise RuntimeError('Run with python 3')

# General settings
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
ARCHIVE_PATH = '/home/service/pylint_pyexplabsys/PyExpLabSys'
SKIP_FILE_LINESTART = ('# Form implementation generated from reading ui file',)
GIT_PREFIX_ARGS = ['git', '-C', ARCHIVE_PATH]
PYLINTRC = os.path.join(
    THIS_DIR , '..', '..', '..', 'bootstrap', '.pylintrc'
)
PYLINT_VERSION = subprocess.check_output(['pylint3 --version 2> /dev/null'], shell=True)
CACHE_PATH = os.path.join(THIS_DIR, 'lint_cache')
SQL_SERVER = '127.0.0.1'
SQL_PORT = 9000


# Helper function
def git(argument_line, python_args=None, only_return_code=False, log_output=False):
    """Perform git command with prefix"""
    if python_args:
        argument_line = argument_line.format(*python_args)
    args = argument_line.split(' ')

    process = subprocess.Popen(
        GIT_PREFIX_ARGS + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = process.communicate()
    out = out.decode('utf-8')
    err = err.decode('utf-8')
    process.stdout.close()
    process.stderr.close()

    if process.returncode != 0:
        LOG.warning('git command %s produced stderr:\n%s', argument_line, err)

    if log_output:
        LOG.debug('git command %s exited with error code %s and output:\n%s',
                  argument_line, process.returncode, out)

    if only_return_code:
        return process.returncode
    else:
        return out


# Functions
def update_git():
    """Updates the PyExpLabSys archive and returns a list of all hashes"""
    LOG.debug('Update git ... %s', ARCHIVE_PATH)
    git('checkout master')
    return_code = git('pull', only_return_code=True)

    if return_code == 0:
        LOG.debug('Updated git successfully!')
    else:
        LOG.debug('Updated git failed')
        raise SystemExit()

    # get list of all commits and reverse
    out = git('log --pretty=format:%H')
    list_of_commits = out.split('\n')  # pylint: disable=no-member
    number_of_commits = len(list_of_commits)
    LOG.debug('Found %s commits in archive', number_of_commits)
    list_of_commits = reversed(list_of_commits)
    return list_of_commits, number_of_commits


def get_commits_in_db():
    """Returns the last commit from the database"""
    LOG.debug('Get last commit from db with user pylint')
    with MySQLdb.connect(SQL_SERVER, 'pylint', 'pylint', 'cinfdata', port=SQL_PORT) as cursor:
        query = "select distinct(commit) from pylint"
        cursor.execute(query)
        commits_in_db = set(item[0] for item in cursor.fetchall())
        LOG.debug('Found %s commits in database', len(commits_in_db))
    return commits_in_db


class CommitAnalyzer(object):
    """Class that runs pylint on a commit and collects stats on it"""

    try:
        with open(CACHE_PATH, 'rb') as file_:
            lint_cache = pickle.load(file_)

        cached_pylint_version = lint_cache.pop('pylint_version')
        if cached_pylint_version != PYLINT_VERSION:
            LOG.error('pylint version has changed, re-run on entire archive')
            raise RuntimeError('pylint version has changed, re-run on entire archive')
        LOG.info('pylint version OK')

        LOG.info('Reloaded cache with %s elements', len(lint_cache))
        if len(lint_cache) > 2000:
            LOG.debug('Lint cache too big (>2000 results), reducing to 1900 elements')
            while len(lint_cache) > 1900:
                lint_cache.popitem(last=False)
            LOG.info('Lint cache length after reduction %s', len(lint_cache))
    except FileNotFoundError:  # pylint: disable=bare-except
        lint_cache = OrderedDict()
        LOG.info('Initialize new cache')

    def __init__(self, commit, send_to_database=True):
        self.send_to_database = send_to_database
        self.commit = commit
        self.error_counter = Counter()
        self.file_counter = {}
        self.total_line_count = 0
        self.total_py3_line_count = 0
        self.file_error_json = {}
        # Checkout commit
        LOG.info('Checkout %s', commit)
        return_code = git('checkout {}', [commit], only_return_code=True)
        if return_code != 0:
            raise RuntimeError("Git checkout of commit %s failed", commit)
        # Find commit time as unix time stamp
        self.commit_time = git("log {} --pretty=format:%ct -n 1".format(commit))

        # Form database connections and cursors
        self.hall_connection = MySQLdb.connect(SQL_SERVER, 'hall', 'hall', 'cinfdata', port=SQL_PORT)
        self.hall_connection.autocommit(True)
        self.hall_cursor = self.hall_connection.cursor()
        self.pylint_connection = MySQLdb.connect(SQL_SERVER, 'pylint', 'pylint', 'cinfdata', port=SQL_PORT)
        self.pylint_connection.autocommit(True)
        self.pylint_cursor = self.pylint_connection.cursor()

    def run_all(self):
        """Run pylint and gather statistics"""
        start = time.time()
        LOG.debug('lint and stats on commit: %s (on . per file analyzed)',
                  self.commit)
        for root, _, files in os.walk(ARCHIVE_PATH):
            # Skip all files in the thirdpart folder
            if root.endswith('thirdparty'):
                LOG.debug('Skipping thirdparty: %s', root)
                continue

            # Skip path relative to base and skip if starts with archive
            relative_path = os.path.relpath(root, ARCHIVE_PATH)
            if relative_path.startswith('archive'):
                LOG.debug('Skipping archive dir: %s', relative_path)
                continue

            for file_ in files:
                filepath = os.path.join(root, file_)

                # If it is not a python file, continue
                if os.path.splitext(filepath)[1].lower() != '.py':
                    LOG.debug('Skipping, is not a python file: %s', filepath)
                    continue

                # If the path does not exist (broken link) continue
                try:
                    os.stat(filepath)
                except OSError as exception:
                    if exception.errno == errno.ENOENT:
                        continue
                    else:
                        raise exception
                # We are good to lint the file
                should_lint = self.add_lines_to_total_count(filepath)
                if should_lint:
                    self.lint_file(filepath)

        if not RUNNING_IN_CRON:
            sys.stdout.write('\n')
        run_time = time.time() - start
        LOG.info('############# Totals #############')
        LOG.info('Ran in %s seconds', run_time)
        LOG.info('ERROR_COUNTER: %s', sum(self.error_counter.values()))
        LOG.info('FILE_COUNTER: %s', sum(self.file_counter.values()))
        LOG.info('TOTAL_LINE_COUNT: %s', self.total_line_count)
        LOG.info('TOTAL_PY3_LINE_COUNT: %s', self.total_py3_line_count)
        LOG.info('CACHE SIZE: %s', len(self.lint_cache))
        LOG.info('############# Totals #############')

        if self.send_to_database:
            self.report_to_mysql()

    def add_lines_to_total_count(self, filename):
        """Add line number statistics and check whether file should be skipped
        altogether based on *file contents*.

        NOTE: Skips based of filenames and paths are performed elsewhere

        Returns:
            bool: Whether this file was included in the line numbers and therefore should
                be linted

        """
        LOG.debug(
            'Adding file to total line count: %s. Line count before: %s',
            filename, self.total_line_count,
        )
        with open(filename) as file_:
            # For files with no lines, the for loop will never start and so we have to
            # make sure line_number is initialized
            line_number = 0
            is_python3_compatible = False
            for line_number, line in enumerate(file_, start=1):
                if line.startswith('python3_only(') or line.startswith('python2_and_3('):
                    is_python3_compatible = True
                for linestart in SKIP_FILE_LINESTART:
                    if line.startswith(linestart):
                        return False
            self.total_line_count += line_number

            # Add Python 3 compatible lines
            if is_python3_compatible:
                self.total_py3_line_count += line_number

        LOG.debug('Line count after: %s', self.total_line_count)
        return True

    def lint_file(self, filepath):
        """Runs lint on the file"""
        LOG.debug('Run pylint on: %s', filepath)

        # Check if we already linted a file like this one
        with open(filepath, 'rb') as file_:
            md5sum = hashlib.md5(file_.read()).hexdigest()
        if md5sum in self.lint_cache:
            out = self.lint_cache[md5sum]
            LOG.debug('Using lint cache for %s', md5sum)
            if not RUNNING_IN_CRON:
                sys.stdout.write('r')
                sys.stdout.flush()
        else:
            if not RUNNING_IN_CRON:
                sys.stdout.write('c')
                sys.stdout.flush()
            LOG.debug('No lint cache found for %s, actually run pylint', md5sum)
            # Collect lint statistics
            args = [
                'pylint3', '--output-format=json', '--disable=no-member',
                '--disable=import-error', '-r', 'n', '--rcfile={}'.format(PYLINTRC),
                filepath,
            ]
            process = subprocess.Popen(args, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            out, _ = process.communicate()
            out = out.decode('utf-8')
            LOG.debug('pylint on file exit code %s', process.returncode)

            if process.returncode == 0:
                out = '[]'

            # Make sure to close file descriptors
            process.stdout.close()
            process.stderr.close()

            # Write to the cache
            CommitAnalyzer.lint_cache[md5sum] = out

        # Calculate relative path
        relative_path = filepath.replace(ARCHIVE_PATH + os.sep, '')

        if out == '[]':
            self.file_error_json[relative_path] = 'null'
        else:
            self.file_error_json[relative_path] = out

        errors = json.loads(out)

        # Form error couter from error symbols, e.g. syntax-error
        self.error_counter += Counter(msg['symbol'] for msg in errors)
        LOG.debug('Found errors: %s', self.error_counter)
        # Add error count for this file
        self.file_counter[relative_path] = len(errors)
        LOG.debug('%s error in file %s', len(errors), relative_path)

    def report_to_mysql(self):
        """Reports the error to mysql

        For the dateplot:
           id 164 is pylint_errors
           id 165 is lines_of_code
           id 169 is lines_of_py3_code
        """
        LOG.info('Report totals to MySQL with hall user')
        query = ('INSERT INTO dateplots_hall (time, type, value) VALUES '
                 '(FROM_UNIXTIME(%s), %s, %s)')
        # 164 is pylint errors and 165 is number of lines
        LOG.debug('Using query: %s', query)

        # Error count
        values = (self.commit_time, 164, sum(self.error_counter.values()))
        LOG.debug('Sending: %s', values)
        self.hall_cursor.execute(query, values)

        # Total number of lines
        values = (self.commit_time, 165, self.total_line_count)
        LOG.debug('Sending: %s', values)
        self.hall_cursor.execute(query, values)

        # Total number of py3 lines
        values = (self.commit_time, 169, self.total_py3_line_count)
        LOG.debug('Sending: %s', values)
        self.hall_cursor.execute(query, values)
        LOG.debug('Total number of errors and lines sent to mysql')

        LOG.info('Report error and file stats to MySQL with pylint user')
        query = ('INSERT INTO pylint (time, identifier, isfile, value, commit, '
                 'pytlin_output_json) VALUES (FROM_UNIXTIME(%s), %s, %s, %s, %s, %s)')
        LOG.debug('Using query: %s', query)

        # Send error stats
        for key, value in self.error_counter.items():
            values = (self.commit_time, key, False, value, self.commit, None)
            self.pylint_cursor.execute(query, values)
            LOG.debug('Sending: %s', values)

        # Send file stats
        for key, value in self.file_counter.items():
            error_json = self.file_error_json[key]
            values = (self.commit_time, key, True, value, self.commit, error_json)
            self.pylint_cursor.execute(query, values)
            LOG.debug('Sending: %s ... (json left out)', values[:5])

        LOG.debug('Everything else sent to mysql')


def main():
    """Runs lint on all python files and reports the result"""
    commits_in_archive, number_of_commits_in_archive = update_git()
    commits_in_db = get_commits_in_db()

    # Lint commit that are not already in the db
    for commit_number, commit in enumerate(commits_in_archive, start=1):
        if commit not in commits_in_db:
            LOG.info('Analyzing commit number %s out of %s from archive', commit_number,
                     number_of_commits_in_archive)
            commit_analyzer = CommitAnalyzer(commit, send_to_database=True)
            commit_analyzer.run_all()
        else:
            LOG.info('Commit number %s (%s) out of %s from archive already analyzed',
                     commit_number, commit, number_of_commits_in_archive)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        LOG.exception("Uh oh, an uncaught exception")
    finally:
        CommitAnalyzer.lint_cache['pylint_version'] = PYLINT_VERSION
        with open(CACHE_PATH, 'wb') as lint_file:
            pickle.dump(CommitAnalyzer.lint_cache, lint_file)
        LOG.info('Dumped cache with %s elements', len(CommitAnalyzer.lint_cache))

    LOG.debug('All done!')
