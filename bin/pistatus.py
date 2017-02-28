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

import sys
import shutil
import socket
from textwrap import wrap
from functools import partial
from subprocess import check_output
from os.path import expanduser, join, isdir, isfile, abspath
from os import getlogin, listdir, sep, chdir, getcwd, popen

if sys.version_info.major < 3:
    print("This script is Python 3 or above only")
    raise SystemExit(1)

# Terminal width
COL = 80
if sys.version_info.minor > 2:
    COL, _ = shutil.get_terminal_size((78, 40))
else:
    # This will most likely fail on non-Linux platforms, in that case
    # just ignore and use default
    try:
        _, COL = [int(num) for num in popen('stty size', 'r').read().split()]
    except:  # pylint: disable=bare-except
        pass

WIDTH = COL - 4
# Machine folder
HOSTNAME = socket.gethostname()
MACHINE_DIR = join(expanduser('~'), 'PyExpLabSys', 'machines', HOSTNAME)
if not isdir(MACHINE_DIR):
    MACHINE_DIR = None

# key width default
KEY_WIDTH = 16

# Username
USERNAME = getlogin()
SCREEN_FOLDER = join(abspath(sep), 'var', 'run', 'screen', 'S-' + USERNAME)


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

    try:
        screens = listdir(SCREEN_FOLDER)
    except FileNotFoundError:
        screens = (())
    if screens:
        framed(blue('Screens'))
        for screen in screens:
            framed(screen)
    else:
        value_pair('Screens', 'None')

    processes = check_output('ps -eo command', shell=True).decode('utf-8')\
        .split('\n')
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

    # older gits did not have the -C options, to change current
    # working directory internally, so we have to do it manually
    cwd = getcwd()
    chdir(join(expanduser("~"), "PyExpLabSys"))

    # date of last commit
    last_commit = check_output(
        'git log --date=iso -n 1 --pretty=format:"%ad"',
        shell=True,
    ).decode('utf-8')
    value_pair('Last commit', last_commit)

    # git clean
    git_status = check_output('git status --porcelain', shell=True)
    if len(git_status) == 0:
        value_pair('Git clean', YES)
    else:
        value_pair('Git clean', NO)

    # Change cwd back
    chdir(cwd)

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
