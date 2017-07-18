#!/usr/bin/env python
# coding=utf-8

"""Generates the module overview, including Python 2/3 status, for the docs"""

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
# Regular expressions for finding the module docstring, in order of decreasing likelyhood
COMMENT = [re.compile(r'\n"""(.*?)"""', re.S),
           re.compile(r'^"""(.*?)"""', re.S),
           re.compile(r'\n\'\'\'(.*?)\'\'\'', re.S),
           re.compile(r'^\'\'\'(.*?)\'\'\'', re.S),]
INFERRED_REFERENCE = '[#inferred]_'
NO_DESCRIPTION = 'NO DESCRIPTION'

# List for all doc content
ALL_FILES = []


def single_file_py23_status(filepath):
    """Extract the Python 2/3 status from a file"""
    with open(filepath, 'rb') as file_:
        for line in file_:
            for pattern in STATUSES.keys():
                if pattern.match(line):
                    return STATUSES[pattern]

        # The INFERRED_REFERENCE at the end, will turn into a comment that explains that
        # this status is inferred
        return r'Python 2 only ' + INFERRED_REFERENCE


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
    description = NO_DESCRIPTION
    with codecs.open(filepath, encoding=encoding) as file_:
        content = file_.read()
        # Look for the earlist comment match and make sure first match will be saved
        found_at = len(content) * 10
        for COMMENT_RE in COMMENT:
            search = COMMENT_RE.search(content)
            if search:
                if search.start() < found_at:
                    comment = search.group(1).strip()
                    description = comment.split('\n\n')[0].replace('\n', ' ')
                    found_at = search.start()

    return description, content


def single_file_status(filepath):
    """Get the status for a single file"""
    # Get the Python 2 and 3 status
    status = single_file_py23_status(filepath)

    # Get the description
    description, content = single_file_description(filepath)

    # Whole path looks like:
    # /home/kenni/PyExpLabSys/doc/source/../../PyExpLabSys/common/sql_saver.py
    # break of the path after /../../
    reduced_filepath = filepath.split('{0}..{0}..{0}'.format(os.sep))[1]
    # Split of extension, so it is: PyExpLabSys/common/sql_saver
    reduced_filepath = os.path.splitext(reduced_filepath)[0]
    # and replace the separators with . so it turns into: PyExpLabSys.common.sql_saver
    module_filepath = reduced_filepath.replace(os.sep, '.')

    # Make module name
    module_name = module_filepath.split('.')[-1]

    return {
        'module_path': module_filepath, 'module_name': module_name,
        'description': description, 'status': status,
        'content': content,
    }


def allfiles_statuses():
    """Gather the file statuses"""
    statuses = []
    # Find all python file in PyExpLabSys
    for dirpath, _, filenames in os.walk(PYEXPLABSYSDIR):
        for filename in filenames:
            if filename == '__init__.py':
                continue
            if os.path.splitext(filename)[1] != '.py':
                continue
            filepath = os.path.join(dirpath, filename)
            try:
                statuses.append(single_file_status(filepath))
            except Exception:  # pylint: disable=broad-except
                statuses.append((filepath, 'ERROR', False, 'ERROR'))

    return statuses

def get_all_docs():
    """Return a list with all doc file content"""
    if ALL_FILES:
        return ALL_FILES

    for root, _, files in os.walk(THIS_DIR):
        for file_ in files:
            if os.path.splitext(file_)[1] != '.rst':
                continue
            with open(os.path.join(root, file_), 'rb') as file_descriptor:
                raw = file_descriptor.read()
                ALL_FILES.append(raw.decode('utf-8'))

    return ALL_FILES


def create_module_link(status):
    """Generate a module link from the status

    Args:
        status (dict): The status dict for a module

    This link title will be the module name and the link it will link to the:
       <subpackage>-doc-<modulename>
    section. The subpackage is e.g. drivers or common.

    For non-driver-files, this function will look though all the
    documentation files, to see if the the label is defined.

    """
    section = status['module_path'].split('.')[1]
    ref = '{section}-doc-{module_name}'.format(section=section, **status)
    label = '.. _{ref}:'.format(ref=ref)

    # Check if we should generate a link or not. For drivers we always
    # do, because we have stubs for everything. For all other modules,
    # we check whether the label is defined anywhere in the
    # documentation files.
    generate_link = False
    if section != 'drivers':
        for content in get_all_docs():
            if label in content:
                generate_link = True
                break
    else:
        generate_link = True


    if generate_link:
        return ':ref:`{module_path} <{ref}>`'.format(ref=ref, **status)
    else:
        return '*' + status['module_path'] + '*'


def write_statuses(statuses):
    """Write the Python 3 statistics out to a restructured text file"""
    print('FILE ALREADY EXISTS:', os.path.isfile(PY3STATPATH))
    if os.path.isfile(PY3STATPATH):
        os.remove(PY3STATPATH)

    # Generate links
    for status in statuses:
        status['module_link'] = create_module_link(status)

    with codecs.open(PY3STATPATH, 'w', encoding='utf8') as file_:
        for status in statuses:
            print('{module_link} ({status})\n\n* {description}\n\n-----\n'.format(**status),
                  file=file_)

def generate_py3_stat():
    """Gather the stats and write them out in restructured text"""
    statuses = allfiles_statuses()
    write_statuses(statuses)


generate_py3_stat()
