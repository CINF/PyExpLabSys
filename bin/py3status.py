#!/usr/bin/env python3

"""Produce Python 3 porting status"""

from __future__ import print_function, division
import errno
import codecs
import argparse
from operator import itemgetter
from os import path, walk, stat

from PyExpLabSys.common.supported_versions import python3_only
python3_only(__file__)

THISDIR = path.dirname(path.realpath(__file__))
BASEPATH = path.dirname(THISDIR)


def collect_all_python_filepaths(skip_machines):
    """Collect all Python file paths respecting ignores etc.

    Args:
        skip_machines (bool): Whether to skip the machines folder
    """
    collected_files = []
    print('Using {} as basepath'.format(BASEPATH))
    for root, _, files in walk(BASEPATH):
        # Skip all files in the thirdpart folder
        if root.endswith('thirdparty'):
            continue

        # Skip path relative to base and skip if starts with archive
        relative_path = path.relpath(root, BASEPATH)
        if relative_path.startswith('archive'):
            continue
        if skip_machines and relative_path.startswith('machines'):
            continue

        for file_ in files:
            filepath = path.join(root, file_)

            # If it is not a python file, continue
            if path.splitext(filepath)[1].lower() != '.py':
                continue

            # Skip if is filepath is a link
            if path.islink(filepath):
                continue

            # If the path does not exist (broken link) continue
            try:
                stat(filepath)
            except OSError as exception:
                if exception.errno == errno.ENOENT:
                    continue
                else:
                    raise exception

            # We are good to lint the file
            collected_files.append(filepath)
    return collected_files


def analyze_files(files):
    """Analyze all the files"""
    total_line_count = 0
    python3_line_count = 0
    non_python_3_files = {}
    for filepath in files:
        # Look throgh the file and look for python 3 support and count lines
        python3_compat = False
        line_number = 0
        with codecs.open(filepath, encoding='utf-8') as file_:
            for line_number, line in enumerate(file_, start=1):
                if line.startswith('python2_and_3(') or\
                   line.startswith('python3_only('):
                    python3_compat = True

        # Save line numbers
        if python3_compat:
            python3_line_count += line_number
        total_line_count += line_number

        # Add the filepath and line number to a dict for non Py3
        relative_path = path.relpath(filepath, BASEPATH)
        if not python3_compat:
            non_python_3_files[relative_path] = line_number
    return total_line_count, python3_line_count, non_python_3_files


def parse_args():
    """Return the parsed command line arguments"""
    parser = argparse.ArgumentParser(description='Display python 3 status')
    parser.add_argument('--skip_machines', '-s', action='store_true', default=False,
                        help='Skip machines. Also in totals.')
    args = parser.parse_args()
    return args


def main():
    """Main function"""
    args = parse_args()

    python_files = collect_all_python_filepaths(args.skip_machines)
    print('Found {} Python files'.format(len(python_files)))
    total_line_count, python3_line_count, non_python_3_files = analyze_files(python_files)

    # Print out stats of black sheeps
    print("Non Python 3 compatible files")
    for filepath, line_num in sorted(non_python_3_files.items(), key=itemgetter(1)):
        print('{: <4} {}'.format(line_num, filepath))
    print('{: <4} {}'.format(sum(non_python_3_files.values()), "Total"))

    # Print out totals
    print('\n{} out {} lines is Python 3 compatible ({:.1%})'.format(
        python3_line_count, total_line_count, python3_line_count / total_line_count))


main()
