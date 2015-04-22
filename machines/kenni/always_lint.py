"""Module to log the number of pylint errors in PyExpLabSys"""

from __future__ import print_function
import os
LOGFILE = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'always_lint.log'
)
import re
import errno
import subprocess
import MySQLdb
from collections import Counter
# Configure logging
import logging
import logging.handlers
LOG = logging.getLogger('always_lint')
LOG.setLevel(logging.DEBUG)
ROTATING_FILE_HANDLER = logging.handlers.RotatingFileHandler(
              LOGFILE, maxBytes=10485760, backupCount=10
)
FORMATTER = logging.Formatter(
    '%(asctime)s:%(name)s: %(levelname)s: %(message)s'
)
ROTATING_FILE_HANDLER.setFormatter(FORMATTER)
LOG.addHandler(ROTATING_FILE_HANDLER)

MATCH_RE = re.compile(r'[^:]+:[0-9]+: \[([A-Z][0-9]+)\(.*\].*')
ARCHIVE_PATH = '/home/kenni/pylint_pyexplabsys/PyExpLabSys'
GIT_ARGS = ['git', '-C', ARCHIVE_PATH, 'pull']
ERROR_COUNTER = Counter()
FILE_COUNTER = Counter()
TOTAL_LINE_COUNT = 0
PYLINTRC = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '..', '..', 'bootstrap',
    '.pylintrc'
)


def update_git(root_path):
    """Updates the PyExpLabSys archive and returns the hash of the last
    commit

    """
    LOG.debug('Update git ... {}'.format(root_path))
    return_value = subprocess.call(GIT_ARGS)

    if return_value == 0:
        LOG.debug('Updated git successfully!')
    else:
        LOG.debug('Updated git failed')
        raise SystemExit()

    # get hash of last commit
    args = ['git', '-C', ARCHIVE_PATH, 'log', '--pretty=format:\'%ct;%H\'',
            '-n', '1']
    process = subprocess.Popen(args, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    out, _ = process.communicate()
    commit_time, commit_hash = out.strip("'").split(';')

    LOG.debug('Get hash of last commit finished with exit status: {}'.format(
        process.returncode))
    LOG.debug('Now at {} from {}'.format(commit_hash, commit_time))

    # Make sure to close file descriptors
    process.stdout.close()
    process.stderr.close()

    return commit_time, commit_hash


def add_lines_to_total_count(filename):
    """Returns the number of lines in file"""
    global TOTAL_LINE_COUNT  # pylint: disable=global-statement
    LOG.debug('Adding file to total line count: {}. Line count before: {}'.format(
        filename, TOTAL_LINE_COUNT))
    with open(filename) as file_:
        for _ in file_:
            TOTAL_LINE_COUNT += 1
    LOG.debug('Line count after: {}'.format(TOTAL_LINE_COUNT))


def lint_file(filepath):
    """Runs lint on the file"""
    LOG.debug('Lint: {}'.format(filepath))

    # Add line count
    add_lines_to_total_count(filepath)

    # Collect lint statistics
    args = ['pylint',
            '--msg-template={path}:{line}: [{msg_id}({symbol}), {obj}] {msg}',
            '--disable=F0401', '-r', 'n',
            '--rcfile={}'.format(PYLINTRC), filepath]
    process = subprocess.Popen(args, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    out, _ = process.communicate()
    LOG.debug('pylint on file exit code {}'.format(process.returncode))

    # Add to error count and file count stats
    for line in out.split('\n'):
        if line == '':
            continue
        LOG.debug('Pylint output line: {}'.format(line))
        match = MATCH_RE.match(line)
        if match:
            LOG.debug('Found error line: {}'.format(line))
            ERROR_COUNTER[match.group(1)] += 1
            LOG.debug('Error type: {}'.format(match.group(1)))
            FILE_COUNTER[filepath.replace(ARCHIVE_PATH + os.sep, '')] += 1

    # Make sure to close file descriptors
    process.stdout.close()
    process.stderr.close()


def report_to_mysql(commit_time, last_commit_hash):
    """Reports the error to mysql"""
    LOG.debug('Report total to MySQL with hall user')
    con = MySQLdb.connect('servcinf', 'hall', 'hall', 'cinfdata')
    cursor = con.cursor()
    query = ('INSERT INTO dateplots_hall (time, type, value) VALUES '
             '(FROM_UNIXTIME(%s), %s, %s)')
    # 164 is pylint errors and 165 is number of lines
    LOG.debug('Using query: {}'.format(query))
    LOG.debug('Sending: {}'.format((commit_time, 164, sum(ERROR_COUNTER.values()))))
    cursor.execute(query, (commit_time, 164, sum(ERROR_COUNTER.values())))
    LOG.debug('Sending: {}'.format((commit_time, 165, TOTAL_LINE_COUNT)))
    cursor.execute(query, (commit_time, 165, TOTAL_LINE_COUNT))
    con.commit()
    con.close()
    LOG.debug('Total number of errors and lines sent to mysql')

    LOG.debug('Report error and file stats to MySQL with pylint user')
    con = MySQLdb.connect('servcinf', 'pylint', 'pylint', 'cinfdata')
    cursor = con.cursor()
    query = ('INSERT INTO pylint (time, identifier, isfile, value, commit) '
             'VALUES (FROM_UNIXTIME(%s), %s, %s, %s, %s)')
    LOG.debug('Using query: {}'.format(query))
    # Send error stats
    for key, value in ERROR_COUNTER.items():
        cursor.execute(query,
            (commit_time, key, False, value, last_commit_hash))
        LOG.debug('Sending: {}'.format((commit_time, key, False, value, last_commit_hash)))
    # Send file stats
    for key, value in FILE_COUNTER.items():
        cursor.execute(query,
            (commit_time, key, True, value, last_commit_hash))
        LOG.debug('Sending: {}'.format((commit_time, key, True, value, last_commit_hash)))
    con.commit()
    con.close()
    LOG.debug('Everything else sent to mysql')


def get_last_commit_from_db():
    """Returns the last commit from the database"""
    LOG.debug('Get last commit from db with user pylint')
    con = MySQLdb.connect('servcinf', 'pylint', 'pylint', 'cinfdata')
    cursor = con.cursor()
    query = "select commit from pylint order by time desc limit 1"
    cursor.execute(query)
    last_hash_in_db = cursor.fetchone()[0]
    con.close()
    LOG.debug('Got: {}'.format(last_hash_in_db))
    return last_hash_in_db


def main(root_path):
    """Runs lint on all python files and reports the result"""
    commit_time, last_commit_hash = update_git(root_path)
    last_commit_hash_in_db = get_last_commit_from_db()
    LOG.debug("Last in file {} at {}".format(last_commit_hash, commit_time))
    LOG.debug("Last in db {}".format(last_commit_hash_in_db))

    if last_commit_hash == last_commit_hash_in_db:
        LOG.debug("No new commits to log. We are done!")
        return
    else:
        LOG.debug("There is a new commit. Proceed to linting.")

    for root, _, files in os.walk(root_path):
        # Skip thirdpart
        if root.endswith('thirdparty'):
            LOG.debug('Skipping thirdparty: {}'.format(root))
            continue

        # Skip relpath
        if os.path.relpath(root, root_path).startswith('archive'):
            LOG.debug('Skipping archive: {}'.format(os.path.relpath(root, root_path)))
            continue

        for file_ in files:
            filepath = os.path.join(root, file_)

            # If it is not a python file, continue
            if os.path.splitext(filepath)[1].lower() != '.py':
                LOG.debug('Skipping, is not a python file: {}'.format(filepath))
                continue

            # If the path does not exist (broken link) continue
            try:
                os.stat(filepath)
            except OSError as exception:
                if exception.errno == errno.ENOENT:
                    LOG.error('Path "{}" does not exist'.format(filepath))
                    continue
                else:
                    raise exception

            # We are good to lint the file
            lint_file(filepath)

    report_to_mysql(commit_time, last_commit_hash)


if __name__ == '__main__':
    # Path of the PyExpLabSys git archive
    main(ARCHIVE_PATH)
    LOG.debug('############# Totals #############')
    LOG.debug('ERROR_COUNTER: {}'.format(ERROR_COUNTER))
    LOG.debug('FILE_COUNTER: {}'.format(FILE_COUNTER))
    LOG.debug('TOTAL_LINE_COUNT: {}'.format(TOTAL_LINE_COUNT))
