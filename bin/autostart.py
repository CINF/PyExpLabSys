#!/usr/bin/env python

"""This script is executed by as a cronjob at every startup and in
responsible for starting up any and all relevant programs in screen

The cronjob is set up to log to /var/log/syslog under the tag: cinfautostart

"""

from __future__ import print_function

from os import path, chdir
from time import sleep
import socket
import subprocess
from functools import partial
from xml.etree import ElementTree as XML


CONFIG = """
# the following two lines give a two-line status, with the current window highlighted
hardstatus alwayslastline
hardstatus string '%{= kG}[%{G}%H%? %1`%?%{g}][%= %{= kw}%-w%{+b yk} %n*%t%?(%u)%? %{-}%+w %=%{g}][%{B}%m/%d %{W}%C%A%{g}]'
bind s split
"""
# Look e.g. at https://gist.github.com/joaopizani/2718397 for more


def parse_args():
    """Parse command line arguments"""
    import argparse
    description = ("Execute all the programs defined in machine/AUTOSTART.xml file "
                   "in screen")
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-m', '--machine', type=str,
                        help='machine name, default is hostname')
    args = parser.parse_args()
    return args


def find_config(args):
    """Find the configuration file"""
    if args.machine is not None:
        machine = args.machine
    else:
        machine = socket.gethostname()

    config_path = path.join(
        path.expanduser('~'), 'PyExpLabSys', 'machines',
        machine, 'AUTOSTART.xml'
    )
    return config_path


def screen_cmd(command, window=None, screen_cmd_base=None, call=None):
    """Execute screen command (with -X) on named session

    Executes: {screen_cmd_base} -p {window} -X {command}

    Where screen_cmd_base is usually: screen -S "{name}"
    and the -p parameter is only filled in, if window is set
    """
    tosend = screen_cmd_base
    if window is not None:
        tosend += ' -p ' + str(window)
    tosend += ' -X ' + command
    call(tosend)


def main():
    """The main script"""
    args = parse_args()
    config_file_path = find_config(args)

    # Change current working directory to config dir
    config_dir = path.dirname(config_file_path)
    chdir(config_dir)

    # Parse XML config file
    etree_object = XML.parse(config_file_path)
    xml = etree_object.getroot()

    # Extract name
    try:
        name = xml.find("name").text
    except AttributeError:
        name = "CINF_SCREEN"

    # Autofill in shell=True and exec in subprocess.call
    call = partial(subprocess.call, shell=True, executable='/bin/bash')

    # Make partial screen command
    screen = partial(screen_cmd, call=call,
                     screen_cmd_base='screen -S "{}"'.format(name))

    call('screen -dmS \"{}\"'.format(name))

    # Reverse the order to end at window 0
    window_number = -1  # To make sure it is defined even without sessions
    for window_number, session in enumerate(xml.findall("session")):
        # Extract startdelay and wait
        delay_element = session.find("startdelay")
        if delay_element is not None:
            delay = float(delay_element.text)
            sleep(delay)

        # Create an extra screen
        screen('screen {}'.format(window_number))


        # Start command
        command = session.find('command').text
        screen(r'stuff "{} $(printf \\r)"'.format(command), window_number)

        # Get title and set
        title = session.find('name').text
        screen('title "{}"'.format(title), window_number)
        
    # Set window title of last window
    screen('title emacs', window_number+1)

    for line in CONFIG.split('\n'):
        if line != '' and not line.startswith('#'):
            screen(line, window=0)

main()
