#!/usr/bin/env python

# Use this in doc source
# .. include:: py3_stat.inc


from __future__ import unicode_literals, print_function
import os
import re
import codecs


# Paths
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
PYEXPLABSYSDIR = os.path.join(THIS_DIR, '..', '..', 'PyExpLabSys')
PY3STATPATH = os.path.join(THIS_DIR, 'py3_stat.inc')

# Regular expressions
PYTHON2_ONLY = re.compile(br'python2_only\(.*\)\s*')
PYTHON3_ONLY = re.compile(br'python3_only\(.*\)\s*')
PYTHON2_AND_3 = re.compile(br'python2_and_3\(.*\)\s*')
STATUSES = {
    PYTHON2_ONLY: 'Python 2 only',
    PYTHON3_ONLY: 'Python 3 only',
    PYTHON2_AND_3: 'Python 2 and 3',
}
ENCODING = re.compile(r'coding[:=]\s*([-\w.]+)')
COMMENT = re.compile(r'^"""(.*?)"""|^\'\'\'(.*?)\'\'\'', re.S)
INFERRED_REFERENCE = '[1]_'
NO_DESCRIPTION = 'NO DESCRIPTION'


def single_file_py23_status(filepath):
    """Extract the Python 2/3 status from a file"""
    with open(filepath, 'rb') as file_:
        for line in file_:
            for pattern in STATUSES.keys():
                if pattern.match(line):
                    return STATUSES[pattern]
        else:
            # The INFERRED_REFERENCE at the end, will turn into a comment that explains that
            # this status is inferred
            return r'Python 2 only\ ' + INFERRED_REFERENCE


def single_file_description(filepath):
    """Extract the description as the first line of the module doc string"""
    # Try to determine encoding
    encoding = 'ascii'
    with open(filepath, 'rb') as file_:
        for line in file_:
            # See if the line is a encoding line and update the encoding
            decoded_line = line.decode(encoding)
            search = ENCODING.search(decoded_line)
            if search:
                encoding = search.group(1)
                break

    # Extract the first line from the module comment
    with codecs.open(filepath, encoding=encoding) as file_:
        content = file_.read()
        search = COMMENT.search(content)
        if search:
            comment = search.group(1).strip()
            description = comment.split('\n\n')[0].replace('\n', ' ')
        else:
            description = NO_DESCRIPTION

    return description
    


def single_file_status(filepath):
    """Get the status for a single file"""
    # Get the Python 2 and 3 status
    status = single_file_py23_status(filepath)

    # Get the description
    description = single_file_description(filepath)

    # Whole path looks like:
    # /home/kenni/PyExpLabSys/doc/source/../../PyExpLabSys/common/sql_saver.py
    # break of the path after /../../
    reduced_filepath = filepath.split('{0}..{0}..{0}'.format(os.sep))[1]
    # and replace the separators with .
    module_filepath = reduced_filepath.replace(os.sep, '.')

    return {'module_path': module_filepath, 'status': status, 'description': description}


def allfiles_statuses():
    """Gather the file statuses"""
    statuses = []
    # Find all python file in PyExpLabSys
    for dirpath, dirnames, filenames in os.walk(PYEXPLABSYSDIR):
        for filename in filenames:
            if filename == '__init__.py':
                continue
            if os.path.splitext(filename)[1] != '.py':
                continue
            filepath = os.path.join(dirpath, filename)
            try:
                statuses.append(single_file_status(filepath))
            except Exception:
                statuses.append((filepath, 'ERROR', False, 'ERROR'))

    return statuses


def vertline(repeats, linestyle='-'):
    """Return a virtical line for use in restructured text tables

    Args:
        repeats (list): List of column widths
        linestyle (str): The line style, defaults to '-'

    Looks like this:
    +----------------------------------------+----------+------------------+
    """
    line = '+' + ('{}' + '+') * len(repeats)
    line = line.format(*[linestyle * repeat for repeat in repeats])
    return line


def write_statuses(statuses):
    """Write the Python 3 statistics out to a restructured text file"""
    # Get largest path and description and set columns width
    largest_path = max([len(status['module_path']) for status in statuses])
    largest_description = max([len(status['description']) for status in statuses])
    column_widths = [largest_path + 2, 22, largest_description + 2]

    # Make separators
    normal_sep = vertline(column_widths)
    double_sep = vertline(column_widths, linestyle='=')

    # Form the row template, it looks something like this:
    # | {module_path: <40} | {status: <20} | {description: <100} |
    column_names = ['module_path', 'status', 'description']
    row_template = '|'
    for name, width in zip(column_names, column_widths):
        row_template += ' {{{}: <{}}} |'.format(name, width - 2)

    with codecs.open(PY3STATPATH, 'w', encoding='utf8') as file_:
        print(normal_sep, file=file_)
        print(row_template.format(module_path='Module',
                                  status='Python 2/3 status',
                                  description='Description'), file=file_)
        print(double_sep, file=file_)
        for status in statuses:
            print(row_template.format(**status), file=file_)
            print(normal_sep, file=file_)

        print(
            '\n'
            '.. rubric:: Footnotes\n'
            '\n'
            '.. [1] For these modules the Python 2/3 status is not indicated directly and so '
            'the status is inferred',
            file=file_)
            


def generate_py3_stat():
    """Gather the stats and write them out in restructured text"""
    statuses = allfiles_statuses()
    write_statuses(statuses)


generate_py3_stat()
