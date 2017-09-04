#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Script to run command on many raspberry pi's at once

Exit codes:
 8  Too low Python version
 9  missing dependency

TODO:
 * Add profile to modify config
 * Add groups
 * If terminator exact layout works, rework layoutting and set positions
 * Refactor modify_config

"""

from __future__ import print_function

from os import path, popen
import sys
import json
import math
import argparse
from subprocess import call
from operator import itemgetter
from collections import OrderedDict

try:
    import requests
    from natsort import natsorted
    from tabulate import tabulate
    from configobj import ConfigObj
except ImportError:
    print("world_of_pi requires the following packages from pypi or package system:\n"\
          "configobj, requests, natsort, tabulate")
    raise SystemExit(9)

if sys.version_info[0] < 3:
    print('World of pi is Python 3 only. Sorry!')
    raise SystemExit(8)

from PyExpLabSys.common.supported_versions import python3_only
python3_only(__file__)


# Read terminal rows and columns
ROWS, COLUMNS = (int(num) for num in popen('stty size', 'r').read().split())


def parse_arguments():
    """Parse the command line arguments"""
    description = (
        'world_of_pi is used to find raspberry pi\'s (possibly according to filters)\n'
        'and to ssh to many pi\'s at once via Terminator'
    )
    parser = argparse.ArgumentParser(description=description,
                                     formatter_class=argparse.RawTextHelpFormatter)
    # Cap help lines at column 64
    filters_help = (
        "Filters used to select raspberry pi's. The are two\n"
        "special filters:\n\n"
        "  all         ->  Used to select all raspberry pi's\n"
        "                  that respond to ping\n"
        "  group GROUP ->  Used to select all raspberry pi's\n"
        "                  in a hardcoded group. (See\n"
        "                  -l or --list-groups for an overview\n"
        "                  of the groups)\n"
        "\n"
        "If none of the special filters are used, the filter\n"
        "string is a Python expression where all the keys for\n"
        "status fields (see -k or --keys for possible values)\n"
        "can be used as variables. E.g:\n\n"
        "  \"host_temperature > 50 or load_average_15m >= 0\"\n"
        "or\n"
        "  \"'B+' in model\"\n"
        "\n"
        "WARNING: eval() is used for the evaluation, so don't do\n"
        "anything silly: https://xkcd.com/327/"
    )
    parser.add_argument('filters', help=filters_help)
    parser.add_argument('-k', '--keys', action='store_true', default=False,
                        help="Print all available keys from filtered pi's")
    parser.add_argument('-l', '--list-groups', action='store_true', default=False,
                        help="List all available groups")
    parser.add_argument('-t', '--terminator', action='store_true', default=False,
                        help="Start ssh in terminator on filtered pi's")
    parser.add_argument('-f', '--fields', help="Explicitely set fields")

    args = parser.parse_args()

    return args

def get_pi_infos():
    """Find all raspberry pi's that respond to ping"""
    # We piggyback onto the information gathering of Roberst hostchecker script
    request = requests.get('http://robertj/hosts.php?get_all=yes')

    # Collect list of statusses
    statuses = []
    for status_json in request.text.split('\n'):
        if status_json == '':
            continue
        status = json.loads(status_json)
        # up = "Down" means can be pinged, but has no status socket
        # up = ""     means cannot be pinged
        if status['up'] == '':
            continue

        # Pull system_status out to upper level
        try:
            system_status = status.pop('sytem_status')
            status.update(system_status)
        except KeyError:
            pass

        # Flatten dictionary
        for key, value in list(status.items()):
            if isinstance(value, dict):
                for inner_key, inner_value in status.pop(key).items():
                    status[key + '_' + inner_key] = inner_value

        statuses.append(status)

    # Turn into hostname -> infodict mapping
    statuses = {status.pop('hostname'): status for status in statuses}
    return statuses


class AccessedDict(dict):
    """Custom dict that records accessed fields"""

    accessed = OrderedDict()

    def __getitem__(self, key):
        self.accessed[key] = None
        return super(AccessedDict, self).__getitem__(key)


def filter_pi(pi_infos, filters):
    """Filter the pi's

    Args:
        pi_infos (dict): All pi_infos
        filters (str): Filter string, may be 'all', 'group GROUP' or general filter string
            which will be eval'ed with info keys as local variables

    Returns:
        tuple: (filtered pi_infos (dict), skipped (list), fields (list))
    """
    if filters == 'all':
        return pi_infos, None, None
    elif filters.startswith('group'):
        raise RuntimeError('Group support is currently not fully implemented')
    else:
        out = {}
        skipped = []
        for hostname, pi_info in pi_infos.items():
            try:
                # Use the pi_info as namespace for the eval and record value access with
                # AccessedDict
                namespace = AccessedDict(pi_info)
                if eval(filters, namespace):
                    out[hostname] = pi_info
            except (TypeError, NameError):
                # TypeError commonly from trying to compare uncompareable types
                skipped.append(hostname)

        # Get the fields list
        fields = list(AccessedDict.accessed.keys())

        return out, skipped, fields


def print_found(pi_infos, keys=False, skipped=None, fields=None):
    """Print out the found pi's

    Args:
        pi_infos (dict): Info for all pi's
        keys (bool): Whether to only print out keys
        skipped (list): Hostnames of skipped pi's
        fields (list): The autodetected used field in the filter

    Returns:
        list: Sorted hostnames
    """
    print()  # Initial new line
    if keys:
        rows, headers, out = print_found_keys(pi_infos)
    else:
        rows, headers, out = print_found_pi(pi_infos, skipped=skipped, fields=fields)
    # Custom style for tabulate (skip horizontal lines between rows but keep between
    # header and rows
    for line in tabulate(rows, headers, tablefmt='fancy_grid').split('\n'):
        if not '├' in line:
            print(line)

    return out


def print_found_keys(pi_infos):
    """Subfunction for print_found, see its docstring

    Returns:
        typle: rows, headers, sorted_keys
    """
    # Find the union of all keys
    keys = set()
    for pi_info in pi_infos.values():
        keys = keys.union(pi_info.keys())

    # Find their types
    types = {}
    example_values = {}
    for key in keys:
        for pi_info in pi_infos.values():
            value = pi_info.get(key)
            if not isinstance(value, type(None)):
                types[key] = type(value).__name__
                example_values[key] = value
                break
        else:
            types[key] = 'NoneType'

    # Sort the keys and form headers and rows
    keys = natsorted(keys)
    headers = ('Key', 'Type', 'Example')
    rows = [(key, types[key], example_values[key]) for key in keys]
    print('Found {} keys:'.format(len(keys)))
    return rows, headers, keys


def print_found_pi(pi_infos, skipped=None, fields=None):
    """Subfunction for print_found, see its docstring

    Returns:
        typle: rows, headers, sorted_keys
    """
    if skipped:  # Works both for None and empty list
        print('The filter failed on {} pi\'s: {}\n'.format(len(skipped), skipped))
    print('Found {} pi\'s that satisfy the filter:'.format(len(pi_infos)))

    # Form headers
    headers = ['Hostname']
    if fields:
        headers += fields

    # Form rows
    rows = []
    for hostname, pi_info in pi_infos.items():
        # Alwyas include hostname and add fields if any
        row = [hostname]
        if fields:
            for field in fields:
                row.append(pi_info.get(field))
        rows.append(row)

    # Natural sort rows by hostname
    rows = natsorted(rows, key=itemgetter(0))
    return rows, headers, [row[0] for row in rows]


def modify_config(pi_infos):
    """Modify the terminator config file and run terminator"""
    configpath = path.join(path.expanduser('~'), '.config', 'terminator', 'config')
    config = ConfigObj(configpath)
    config['layouts']['world_of_pi'] = {}
    layout = config['layouts']['world_of_pi']

    # Global settings
    x_offset = 100
    y_offset = 100
    terms = len(pi_infos)
    x = 1000
    y = 1000

    # Add base child (window)
    layout['child0'] = {
        'order': '0',
        'parent': '',
        'position': '{}:{}'.format(x_offset, y_offset),
        'size': [str(x), str(y)],
        'type': 'Window'
    }

    # Calculate number of rows and columns
    row_n = int(math.floor(math.sqrt(terms)))
    col_n = [terms // row_n]
    col_n.append(terms - sum(col_n))

    terminal_places = [('child0', '0')]
    last_child_num = 0
    # Make rows
    while len(terminal_places) < row_n:
        new_terminal_places = []
        for place_num, (parent, order) in enumerate(terminal_places):
            remaining = len(terminal_places) - place_num - 1#  + len(new_terminal_places)
            # if the number of proginal slots remaining + the number that will be
            # added is <= row_n
            if remaining + len(new_terminal_places) + 2 <= row_n:
                last_child_num += 1
                new_child_name = 'child' + str(last_child_num)
                place = 200
                layout[new_child_name] = {
                    'order': order,
                    'parent': parent,
                    'position': str(place),
                    'type': 'VPaned'
                }
                new_terminal_places += [(new_child_name, '0'), (new_child_name, '1')]
            else:
                new_terminal_places.append((parent, order))
        terminal_places = new_terminal_places

    # Make columns
    while len(terminal_places) < terms:
        new_terminal_places = []
        for place_num, (parent, order) in enumerate(terminal_places):
            #print(place_num, (parent, order))
            remaining = len(terminal_places) - place_num - 1#  + len(new_terminal_places)
            # if the number of proginal slots remaining + the number that will be
            # added is <= row_n
            #print('rem', remaining)
            if remaining + len(new_terminal_places) + 2 <= terms:
                last_child_num += 1
                new_child_name = 'child' + str(last_child_num)
                place = 300
                layout[new_child_name] = {
                    'order': order,
                    'parent': parent,
                    'position': str(place),
                    'type': 'HPaned'
                }
                new_terminal_places += [(new_child_name, '0'), (new_child_name, '1')]
            else:
                new_terminal_places.append((parent, order))
        terminal_places = new_terminal_places

    # Add terminals
    for index, (terminal_place, hostname) in enumerate(zip(terminal_places, pi_infos)):
        layout['terminal' + str(index)] = {
            'title': hostname,
            'command': ('ssh -o UserKnownHostsFile=/dev/null '
                        '-o StrictHostKeyChecking=no ' + hostname),
            'group': 'Omnicron',
            'order': terminal_place[1],
            'parent': terminal_place[0],
            'profile': 'pip',
            'type': 'Terminal'
        }

    # Write the config and call teminator
    config.write()
    call('terminator -l world_of_pi', shell=True)


def main():
    """The main function"""
    # Parse args
    args = parse_arguments()
    # Get all pi_info
    pi_infos = get_pi_infos()
    # Filter the pi's
    pi_infos, skipped, fields = filter_pi(pi_infos, args.filters)
    # Print out the found
    if args.fields is not None:
        fields = args.fields.split(',')

    sorted_keys = print_found(pi_infos, args.keys, skipped=skipped, fields=fields)
    # Modify the Terminator config and run
    if args.terminator:
        modify_config(sorted_keys)


main()
