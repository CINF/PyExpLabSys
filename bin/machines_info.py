#!/usr/bin/env python3
# pylint: disable=undefined-loop-variable

"""A machine information command"""

import os
from os.path import expanduser, join, isdir, exists
from collections import Counter, defaultdict
import argparse

from PyExpLabSys.common.supported_versions import python3_only
python3_only(__file__)

POSSIBLE_MACHINE_LOCATIONS = (
    join(expanduser('~'), 'PyExpLabSys', 'machines'),
    join(expanduser('~'), 'code', 'PyExpLabSys', 'machines'),
)
for MACHINE_DIR in POSSIBLE_MACHINE_LOCATIONS:
    if isdir(MACHINE_DIR):
        break
else:
    raise RuntimeError(
        'No machines folder found in {}'.format(POSSIBLE_MACHINE_LOCATIONS)
    )


def gather_statisics():
    """Gather statistics about the machines folder"""
    stats = Counter()
    missing = defaultdict(list)
    for machine_name in os.listdir(MACHINE_DIR):
        machine_dir = join(MACHINE_DIR, machine_name)
        if not isdir(machine_dir):
            continue
        stats['total'] += 1
        for file_ in ('AUTOSTART.xml', 'PURPOSE'):
            abs_path = join(machine_dir, file_)
            if exists(abs_path):
                stats[file_] += 1
            else:
                missing[file_].append(machine_name)
    return stats, missing


def parse_args():
    """Return the parsed command line arguments"""
    description = ('Print statistics about features in the machines folders.')
    parser = argparse.ArgumentParser(description=description)
    command_help = ('The command to execute. Possible commands are: "help", '
                    '"summary" (default), "purpose", "autostart".')
    parser.add_argument('command', default='summary', nargs='?',
                        help=command_help)
    args = parser.parse_args()
    return args


def summary(stats, _):
    """Print out summary"""
    print("In total         :", stats['total'])
    print("Has AUTOSTART.xml:", stats['AUTOSTART.xml'])
    print("Has purpose      :", stats['PURPOSE'])


def purpose(_, missing):
    """Print out the machines that are missing purpose"""
    print("The following machines has no PURPOSE file:")
    for machine_name in missing['PURPOSE']:
        print(machine_name)


def autostart(_, missing):
    """Print out the machines that are missing autostart"""
    print("The following machines has no AUTOSTART.xml file:")
    for machine_name in missing['AUTOSTART.xml']:
        print(machine_name)


def main():
    """Main function"""
    args = parse_args()
    function = globals().get(args.command, None)
    if function is None:
        print('Unknown command "{}". Try "machines_info.py help".'.format(
            args.command))
        raise SystemExit(1)

    stats, missing = gather_statisics()
    function(stats, missing)

main()
