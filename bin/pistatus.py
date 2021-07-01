#!/usr/bin/env python3
# pylint: disable=no-member,invalid-name,no-else-return,global-statement

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

Check settings (only print if wrong)
 * Check the timezone an

"""

from __future__ import print_function
from time import time
import os
from os.path import expanduser, join, isdir, isfile, abspath
from os import getlogin, listdir, sep, chdir, getcwd, popen, environ
import sys
import shutil
import socket
import argparse
from threading import Thread
from textwrap import wrap
from functools import partial
from subprocess import check_output
from PyExpLabSys.common.supported_versions import python2_and_3
T0 = time()
python2_and_3(__file__)
try:
    import getpass
except ImportError:
    pass

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

PYEXPLABSYS_DIR = join(expanduser("~"), "PyExpLabSys")
PYEXPLABSYS_DIR_EXISTS = os.path.isdir(PYEXPLABSYS_DIR)

MACHINE_DIR = join(PYEXPLABSYS_DIR, 'machines', HOSTNAME)
if not isdir(MACHINE_DIR):
    MACHINE_DIR = None

# key width default
KEY_WIDTH = 16

# Username
try:
    USERNAME = getlogin()
except FileNotFoundError:
    USERNAME = getpass.getuser()

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
    if len(purpose_lines) > 1 and purpose_lines[0].startswith('id:') and \
       purpose_lines[1].startswith('purpose:'):
        # Strip the first two lines of id and shorthand purpose
        purpose = ''.join(purpose_lines[2:]).strip()
        if not purpose:
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
    """Collect running programs"""
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
    """Collect last commit"""
    # older gits did not have the -C options, to change current
    # working directory internally, so we have to do it manually
    cwd = getcwd()
    if not PYEXPLABSYS_DIR_EXISTS:
        THREAD_COLLECT['last_commit'] = red('No PyExpLabSys archive')
        return

    chdir(PYEXPLABSYS_DIR)
    last_commit = check_output(
        'git log --date=iso -n 1 --pretty=format:"%ad"',
        shell=True,
    ).decode('utf-8')
    THREAD_COLLECT['last_commit'] = last_commit

    # Change cwd back
    chdir(cwd)


def collect_git_status():
    """Collect git status"""
    # older gits did not have the -C options, to change current
    # working directory internally, so we have to do it manually
    cwd = getcwd()
    if not PYEXPLABSYS_DIR_EXISTS:
        THREAD_COLLECT['git_status'] = None
        return

    chdir(PYEXPLABSYS_DIR)
    git_status = check_output('git status --porcelain', shell=True)
    THREAD_COLLECT['git_status'] = git_status

    # Change cwd back
    chdir(cwd)

def collect_timezone_info():
    """Collect information about the timezone setting"""
    tests = {
        'Time zone': 'Europe/Copenhagen',
        'NTP synchronized': 'yes'
    }
    time_zone_lines = check_output(
        'export LC_ALL=C; timedatectl',
        shell=True,
    ).strip().decode('utf-8').split('\n')
    status = {'pass': True, 'message': '', 'output': time_zone_lines}
    for key, value in tests.items():
        for line in time_zone_lines:
            if key in line:
                if value not in line:
                    status['pass'] = False
                    status['message'] = key + ' is not: ' + value
                break
        else:
            status['pass'] = False
            status['message'] = 'The test key: {} wasn\'t found'.format(key)
            break

    THREAD_COLLECT['timezone'] = status

def time_zone():
    """Display time zone information"""
    status = THREAD_COLLECT['timezone']
    if status['pass']:
        return

    framed('')
    framed(red('Time zone problems'))
    framed(red('=================='))
    framed(red('A configuration issue was found with the time zone settings.'))
    framed(red('The problem was: ' + status['message']))
    framed('')
    framed(red('All output from timedatectl was:'))
    for line in status['output']:
        framed(red(line))


def git():
    """Display the git status"""
    framed(bold('git'))
    framed(bold('==='))

    # date of last commit
    value_pair('Last commit', THREAD_COLLECT['last_commit'])

    # git clean
    if THREAD_COLLECT['git_status'] is None:
        value_pair('Git clean', red('No PyExpLabSys archive'))
    elif THREAD_COLLECT['git_status']:
        value_pair('Git clean', NO)
    else:
        value_pair('Git clean', YES)


def tips():
    """Display tips"""
    framed(bold('tips'))
    framed(bold('===='))
    framed("To run this script use: pistatus.py")
    framed("Open running screen with one key-letter " + bold("s"))
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
    for function in (collect_running_programs, collect_last_commit, collect_git_status,
                     collect_timezone_info):
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
    for thread in threads[1: 3]:
        thread.join()
    git()
    framed('')

    tips()

    threads[3].join()
    time_zone()

    # Footer (include time to run)
    timeline = " {:.2f}s #".format(time() - T0)
    global COL
    COL -= len(timeline)
    hline(end='')
    print(timeline, end='')


main()
