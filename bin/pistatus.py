#!/usr/bin/env python3
# pylint: disable=no-member,invalid-name

"""Small utility script to show commonly used status information about the Raspberry Pi

The information should be broken down into the following sections:

machine status:

 * purpose
 * has autostart?

running programs:

 * display whether there is running a screen
 * display running python programs

git:

 * date of last commit
 * git clean

Pi healt (from SystemStatus) TODO:
 * temperature
 * load
 * etc...

"""

from __future__ import print_function

import shutil
import socket
from textwrap import wrap
from functools import partial
from subprocess import check_output
from os.path import expanduser, join, isdir, isfile

# Terminal width
COL, _ = shutil.get_terminal_size((78, 40))
WIDTH = COL - 4
# Machine folder
HOSTNAME = socket.gethostname()
MACHINE_DIR = join(expanduser('~'), 'PyExpLabSys', 'machines', HOSTNAME)
if not isdir(MACHINE_DIR):
    MACHINE_DIR = None

# key width default
KEY_WIDTH = 16


# Utility functions
def color_(line, color):
    """Print with ansi color"""
    return '\x1b[{}m{}\x1b[0m'.format(color, line)

red = partial(color_, color='1;31')
bold = partial(color_, color='1;37')
green = partial(color_, color='1;32')
blue = partial(color_, color='1;34')
yellow = partial(color_, color='1;33')

YES = green('Yes')
NO = red('NO')


def hline():
    """Prints out a horizontal line"""
    print("#" * COL)


def framed(line, align='<'):
    """Prints out a framed line"""
    ncolors = line.count('\x1b') // 2
    width = WIDTH + ncolors * 11
    print("# {{: {}{}}} #".format(align, width).format(line))


def value_pair(key, value, key_width=KEY_WIDTH):
    """Return a line with a key value pair"""
    if key_width is not None:
        framed(blue('{{: <{}}}'.format(key_width).format(key)) + ': ' + value)
    else:
        framed(blue(key) + ': ' + value)


def machine_status():
    """Output machine status"""
    framed(bold('Machine folder status'))
    framed(bold('====================='))
    # Purpose
    purpose = 'N/A'
    if MACHINE_DIR:
        try:
            with open(join(MACHINE_DIR, 'PURPOSE')) as file_:
                purpose = file_.read()
        except IOError:
            pass

    spaces = ' ' * (KEY_WIDTH - 7)
    purpose_key = 'purpose' + spaces + ': '
    purpose_lines = wrap(purpose, WIDTH, initial_indent=purpose_key)
    framed(purpose_lines[0].replace(purpose_key, blue('Purpose') + spaces + ': '))
    for line in purpose_lines[1:]:
        framed(line)

    # Has autostart
    if MACHINE_DIR and isfile(join(MACHINE_DIR, 'AUTOSTART.xml')):
        value_pair('Has autostart', YES)
    else:
        value_pair('Has autostart', 'NO')


def running_programs():
    """Out running programs status"""
    framed(bold('Running programs'))
    framed(bold('================'))

    processes = check_output('ps -eo command', shell=True).decode('utf-8').split('\n')
    if any('screen' in process for process in processes):
        value_pair('Running screen', YES)
    else:
        value_pair('Running screen', 'NO')
    python_processes = []
    for process in processes:
        if 'python' in process.split(' ')[0]:
            if any(skip in process for skip in ('pistatus', 'pylint')):
                continue
            python_processes.append(process[0: WIDTH])

    if python_processes:
        framed(blue('Python processes'))
        for process in python_processes:
            framed(process)
    else:
        value_pair('Python processes', 'None')


def git():
    """Display the git status"""
    framed(bold('git'))
    framed(bold('==='))

    # date of last commit
    last_commit = check_output('git -C $HOME/PyExpLabSys log --date=iso -n 1 --pretty=format:"%ad"',
                               shell=True).decode('utf-8')
    value_pair('Last commit', last_commit)

    # git clean
    git_status = check_output('git -C $HOME/PyExpLabSys status --porcelain', shell=True)
    if len(git_status) == 0:
        value_pair('Git clean', YES)
    else:
        value_pair('Git clean', NO)

def main():
    """main function"""
    # Header
    hline()
    framed(yellow('Raspberry Pi status ({})'.format(HOSTNAME)), align='^')
    hline()

    machine_status()
    framed('')

    running_programs()
    framed('')

    git()

    # Footer
    hline()


main()
