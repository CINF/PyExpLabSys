"""Module to log the number of pylint errors in PyExpLabSys"""

from __future__ import print_function
import os
import re
import subprocess
import MySQLdb
from collections import Counter
from pylint.lint import Run
from pylint.reporters.text import TextReporter


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


class WriteableObject(object):  # pylint: disable=too-few-public-methods
    """Dummy writeable object"""

    def __init__(self):
        self.content = []

    def write(self, string):
        """Writes a string to content"""
        self.content.append(string)


def update_git(root_path):
    """Updates the PyExpLabSys archive"""
    print("Update git ... ", root_path, end='')
    return_value = subprocess.call(GIT_ARGS)
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
    args = ['--msg-template={path}:{line}: [{msg_id}({symbol}), {obj}] {msg}',
            '-r', 'n', '--rcfile={}'.format(PYLINTRC), filepath]
    output = WriteableObject()
    Run(args, reporter=TextReporter(output), exit=False)
    for line in output.content:
        match = MATCH_RE.match(line)
        if match:
            ERROR_COUNTER[match.group(1)] += 1
            FILE_COUNTER[filepath.replace(ARCHIVE_PATH + os.sep, '')] += 1


def report_to_mysql():
    """Reports the error to mysql"""
    con = MySQLdb.connect('servcinf', 'hall', 'hall', 'cinfdata')
    cursor = con.cursor()
    query = 'INSERT INTO dateplots_hall (type, value) VALUES (%s, %s)'
    # 164 is pylint errors
    cursor.execute(query, (164, sum(ERROR_COUNTER.values())))
    cursor.execute(query, (165, TOTAL_LINE_COUNT))
    con.commit()
    print('Total number of errors sent to mysql')

    con = MySQLdb.connect('servcinf', 'pylint', 'pylint', 'cinfdata')
    cursor = con.cursor()
    query = ('INSERT INTO pylint (identifier, isfile, value) VALUES '
             '(%s, %s, %s)')
    for key, value in ERROR_COUNTER.items():
        cursor.execute(query, (key, False, value))
    for key, value in FILE_COUNTER.items():
        cursor.execute(query, (key, True, value))
    con.commit()
    print('Everything else sent to mysql')


def main(root_path):
    """Runs lint on all python files and reports the result"""
    update_git(root_path)
    for root, _, files in os.walk(root_path):
        if root.endswith('thirdparty'):
            continue
        for file_ in files:
            filepath = os.path.join(root, file_)
            if os.path.splitext(filepath)[1].lower() == '.py':
                lint_file(filepath)

    report_to_mysql()


if __name__ == '__main__':
    # Path of the PyExpLabSys git archive
    main(ARCHIVE_PATH)
