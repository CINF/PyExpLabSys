"""Module to log the number of pylint errors in PyExpLabSys"""

from __future__ import print_function
import os
import re
import time
import errno
import subprocess
import MySQLdb
from collections import Counter


MATCH_RE = re.compile(r'[^:]+:[0-9]+: \[([A-Z][0-9]+)\(.*\].*')
ARCHIVE_PATH = '/home/kenni/pylint_pyexplabsys/PyExpLabSys'
GIT_ARGS = ['git', '-C', ARCHIVE_PATH, 'pull']
ERROR_COUNTER = Counter()
FILE_COUNTER = Counter()
TOTAL_LINE_COUNT = 0
PYLINTRC = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'pylintrc'
)


def update_git(root_path, week_delta):
    """Updates the PyExpLabSys archive"""
    #print("Update git ... ", root_path, end='')
    #return_value = subprocess.call(GIT_ARGS)
    #if return_value == 0:
    #    print(' successfully')
    #else:
    #    print(' failed')
    #    raise SystemExit()

    print("Checkout old ... ", root_path, end='')
    ref_args = ['git', '-C', ARCHIVE_PATH, 'rev-list', '-n', '1',
                '--before="{} weeks ago"'.format(week_delta), 'master']
    process = subprocess.Popen(ref_args, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    out, _ = process.communicate()
    process.stdout.close()
    process.stderr.close()

    return_value = subprocess.call(
        ['git', '-C', ARCHIVE_PATH, 'checkout', out.strip()]
    )
    if return_value == 0:
        print(' successfully')
    else:
        print(' failed')
        raise SystemExit()


def add_lines_to_total_count(filename):
    """Returns the number of lines in file"""
    global TOTAL_LINE_COUNT  # pylint: disable=global-statement
    with open(filename) as file_:
        for _ in file_:
            TOTAL_LINE_COUNT += 1


def lint_file(filepath):
    """Runs lint on the file"""
    print('Lint:', filepath)

    # Add line count
    add_lines_to_total_count(filepath)

    # Collect lint statistics
    args = ['pylint',
            '--msg-template={path}:{line}: [{msg_id}({symbol}), {obj}] {msg}',
            '-r', 'n', '--rcfile={}'.format(PYLINTRC), filepath]
    process = subprocess.Popen(args, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    out, _ = process.communicate()

    for line in out.split('\n'):
        match = MATCH_RE.match(line)
        if match:
            ERROR_COUNTER[match.group(1)] += 1
            FILE_COUNTER[filepath.replace(ARCHIVE_PATH + os.sep, '')] += 1

    process.stdout.close()
    process.stderr.close()


def report_to_mysql(week_delta):
    """Reports the error to mysql"""
    unixtime = time.time() - week_delta * 7 * 24 * 60 * 60

    con = MySQLdb.connect('servcinf', 'hall', 'hall', 'cinfdata')
    cursor = con.cursor()
    query = ('INSERT INTO dateplots_hall (time, type, value) VALUES '
             '(FROM_UNIXTIME(%s), %s, %s)')
    # 164 is pylint errors
    cursor.execute(query, (unixtime, 164, sum(ERROR_COUNTER.values())))
    cursor.execute(query, (unixtime, 165, TOTAL_LINE_COUNT))
    con.commit()
    print('Total number of errors sent to mysql')

    con = MySQLdb.connect('servcinf', 'pylint', 'pylint', 'cinfdata')
    cursor = con.cursor()
    query = ('INSERT INTO pylint (time, identifier, isfile, value) VALUES '
             '(FROM_UNIXTIME(%s), %s, %s, %s)')
    for key, value in ERROR_COUNTER.items():
        cursor.execute(query, (unixtime, key, False, value))
    for key, value in FILE_COUNTER.items():
        cursor.execute(query, (unixtime, key, True, value))
    con.commit()
    print('Everything else sent to mysql')


def main(root_path, week_delta):
    """Runs lint on all python files and reports the result"""
    update_git(root_path, week_delta)
    for root, _, files in os.walk(root_path):
        if root.endswith('thirdparty'):
            continue
        for file_ in files:
            filepath = os.path.join(root, file_)

            # If it is not a python file, continue
            if os.path.splitext(filepath)[1].lower() != '.py':
                continue

            # If the path does not exist (broken link) continue
            try:
                os.stat(filepath)
            except OSError as exception:
                if exception.errno == errno.ENOENT:
                    print('Path "{}" does not exist'.format(filepath))
                    continue
                else:
                    raise exception

            lint_file(filepath)

    report_to_mysql(week_delta)


if __name__ == '__main__':
    # Path of the PyExpLabSys git archive
    for n in range(57, 156):
        print("########", n, "###########")
        ERROR_COUNTER = Counter()
        FILE_COUNTER = Counter()
        TOTAL_LINE_COUNT = 0
        main(ARCHIVE_PATH, n)
        print(ERROR_COUNTER, FILE_COUNTER, TOTAL_LINE_COUNT)
