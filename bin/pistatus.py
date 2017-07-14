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

from time import time
T0 = time()
import sys
import shutil
import socket
import argparse
from threading import Thread
from textwrap import wrap
from functools import partial
from subprocess import check_output
from os.path import expanduser, join, isdir, isfile, abspath
from os import getlogin, listdir, sep, chdir, getcwd, popen, environ

if sys.version_info.major < 3:
    print("This script is Python 3 or above only")
    raise SystemExit(1)

try:
    if environ['TERM'] == 'screen':
        print("In screen. Do not run pistatus.")
        raise SystemExit(2)
except KeyError:
    pass

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

# Parse args for possible other HOSTNAME
def get_hostname():
    """Return the hostname to use"""
    parser = argparse.ArgumentParser(description='Show raspberry pi status')
    parser.add_argument('pi', nargs='?', default=None,
                        help='')
    args = parser.parse_args()
    pi = args.pi
    if pi is None:
        return socket.gethostname()
    else:
        if pi.isdigit():
            return 'rasppi' + pi
        else:
            return pi

# Machine folder
HOSTNAME = get_hostname()


MACHINE_DIR = join(expanduser('~'), 'PyExpLabSys', 'machines', HOSTNAME)
if not isdir(MACHINE_DIR):
    MACHINE_DIR = None

# key width default
KEY_WIDTH = 16

# Username
USERNAME = getlogin()
SCREEN_FOLDER = join(abspath(sep), 'var', 'run', 'screen', 'S-' + USERNAME)

# Dict used to collect data from thread
THREAD_COLLECT = {}

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


def hline(end='\n'):
    """Prints out a horizontal line"""
    print("#" * COL, end=end)


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

    # The purpose files have had two different formats, check for the new one
    purpose_lines = purpose.split('\n')
    # New format
    if len(purpose_lines) > 1 and purpose_lines[0].startswith('id:') and purpose_lines[1].startswith('purpose:'):
        # Strip the first two lines of id and shorthand purpose
        purpose = ''.join(purpose_lines[2:]).strip()
        if len(purpose) == 0:
            purpose = purpose_lines[1].replace('purpose:', '').strip()
            

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


def collect_running_programs():
    processes = check_output('ps -eo command', shell=True).decode('utf-8')\
        .split('\n')
    THREAD_COLLECT['processes'] = processes


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

    python_processes = []
    for process in THREAD_COLLECT['processes']:
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


def collect_last_commit():
    last_commit = check_output(
        'git log --date=iso -n 1 --pretty=format:"%ad"',
        shell=True,
    ).decode('utf-8')
    THREAD_COLLECT['last_commit'] = last_commit


def collect_git_status():
    git_status = check_output('git status --porcelain', shell=True)
    THREAD_COLLECT['git_status'] = git_status


def git():
    """Display the git status"""
    framed(bold('git'))
    framed(bold('==='))

    # older gits did not have the -C options, to change current
    # working directory internally, so we have to do it manually
    cwd = getcwd()
    chdir(join(expanduser("~"), "PyExpLabSys"))

    # date of last commit
    value_pair('Last commit', THREAD_COLLECT['last_commit'])

    # git clean
    if len(THREAD_COLLECT['git_status']) == 0:
        value_pair('Git clean', YES)
    else:
        value_pair('Git clean', NO)

    # Change cwd back
    chdir(cwd)


def tips():
    """Display tips"""
    framed(bold('tips'))
    framed(bold('===='))
    framed("To run this script use: pistatus.py")
    framed("Navigate PyExpLabSys folders with one-letter commands: ")
    framed(" " + bold("a") + "=apps, " + bold("b") + "=bootstrap," +
           " " + bold("c") + "=common, " + bold("d") + "=drivers, ")
    framed(" " + bold("m") + "=this machine folder or machines, " +
           bold("p") + "=~/PyExpLabSys/PyExpLabSys")


def main():
    """main function"""
    # On Raspberry pi it takes time to call command on the command
    # line, so we put the three calls to the command line out into
    # threads
    threads = []
    for function in collect_running_programs, collect_last_commit, collect_git_status:
        thread = Thread(target=function)
        thread.start()
        threads.append(thread)

    # Header
    hline()
    framed(yellow('Raspberry Pi status ({})'.format(HOSTNAME)), align='^')
    hline()


    machine_status()
    framed('')

    # Join the processes thread, since we need the processes output now
    threads[0].join()
    running_programs()
    framed('')

    # Join git threads
    for thread in threads[1:]:
        thread.join()
    git()
    framed('')

    tips()

    # Footer (include time to run)
    timeline = " {:.2f}s #".format(time() - T0)
    global COL
    COL -= len(timeline)
    hline(end='')
    print(timeline, end='')


main()
