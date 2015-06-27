#!/use/local/env python
# pylint: disable=attribute-defined-outside-init,star-args

"""A socket tester program for linux"""

from __future__ import print_function
import sys
import os
import socket
import json
import select
import textwrap
from pprint import pprint
from PyExpLabSys.common.sockets import PUSH_ERROR, PUSH_RET, UNKNOWN_COMMAND
SOCK = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SOCK.setblocking(0)

try:
    import readline
except ImportError:
    readline = None  # pylint: disable=invalid-name

try:
    import colorama
except ImportError:
    colorama = None  # pylint: disable=invalid-name


def clear():
    """Clear the screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


ANSI_FORMATTERS = {
    'bold': '\033[1m',
    'green': '\033[32m',
    'red': '\033[31m',
    'yellow': '\033[33m',
}


def ansi_color(text, format_codes=None, pad=None):
    """A colorizer function"""
    if pad is not None:
        text = '{{: <{}}}'.format(pad).format(text)

    if colorama is None:
        return text

    if format_codes is None:
        format_str = ANSI_FORMATTERS['bold']
    else:
        format_str = ''
        for format_ in format_codes:
            for format_container in [colorama.Fore, colorama.Style]:
                try:
                    format_str += getattr(format_container, format_.upper())
                    break
                except AttributeError:
                    pass
            else:
                message = 'Format "{}" is unknown'.format(format_)
                raise ValueError(message)

    return '{}{}\033[0m'.format(format_str, text)


HEADING = ansi_color('===', ['bright', 'cyan'])
IPPORT = ansi_color('IPADDRESS:PORT', ['bright'])

WELCOME = """
{heading} {greeting} {heading}

This is a basic command-and-reply program. See {help} for more details.
""".format(
    heading=HEADING,
    greeting=ansi_color('Welcome to the socket tester program!',
                        ['bright', 'magenta']),
    help=ansi_color('help', ['bright', 'green']),
)

HELP_BASE = """
{heading} {greeting} {heading}

The socket tester program can be used to test the basic functionality of the
different kinds of sockets in PyExpLabSys.common.sockets.

It is a basic *tab completed commandline interface where you can send commands
to either the test program or the socket.

The commands that the test program understands are:

 * {set_}
       Set the IP addres and port to use and ask the socket which commands and
       codenames it knows about
 * {set_noauto}
       Set the IP addres and port (don't ask the socket about anything, useful
       if the socket is suspected of failing)
 * {help_}Show this help
 * {quit_} or {exit_}Quit the socket tester

All sockets understand the commands: name, status

Besides this, Sockets of type DataPullSocket and DateDataPullSocket
(port default 9000 and 9010) understands these commands:

 * raw, json, raw_wn, json_wn, CODENAME#raw, CODENAME#json
 * codenames_raw, codenames_json

The DataPushSocket (port default 8500) understands these commands:

 * json_wn#DATA
 * raw_wn#DATA

and LiveSocket (port default 8000) understands these commands:

 * data, codenames, sane_interval
""".format(
    heading=HEADING,
    greeting=ansi_color('Help',
                        ['bright', 'magenta']),
    set_=ansi_color('set ', ['bright', 'green']) + IPPORT,
    set_noauto=ansi_color('set_noauto ', ['bright', 'green']) + IPPORT,
    help_=ansi_color('help', ['bright', 'green'], pad=16),
    quit_=ansi_color('quit', ['bright', 'green']),
    exit_=ansi_color('exit', ['bright', 'green'], pad=8),
)


class SocketTimeout(Exception):
    """Socket timeout exception"""


class SocketCompleter(object):  # pylint: disable=too-few-public-methods
    """A command completer for a socket connection"""

    def __init__(self, commands=None):
        self.options = ['quit', 'exit', 'help', 'set', 'set_noauto', 'unset']
        if commands:
            self.options += commands

    def complete(self, text, state):
        """Completer for a socket connection"""
        response = None
        if state == 0:
            # This is the first time for this text, so build a match list.
            if text:
                self.matches = [s for s in self.options
                                if s and s.startswith(text)]
            else:
                self.matches = self.options[:]

        # Return the state'th item from the match list, if we have that many
        try:
            response = self.matches[state]
        except IndexError:
            response = None
        return response


def commands_and_codenames(ip_port, timeout=1):
    """Return information from a socket about commands and codenames"""
    out = []
    for command in ['name', 'commands', 'codenames']:
        SOCK.sendto(command, ip_port)

        ready = select.select([SOCK], [], [], timeout)
        if ready[0]:
            recv = SOCK.recv(65535)
        else:
            raise SocketTimeout()

        if recv in [UNKNOWN_COMMAND, PUSH_ERROR + '#' + UNKNOWN_COMMAND]:
            out.append(None)
            continue

        push_ret_prefix = PUSH_RET + '#'
        if recv.startswith(push_ret_prefix):
            recv = recv[len(push_ret_prefix):]
        if command == 'name':
            out.append(recv)
        else:
            out.append(json.loads(recv))

    return out


class SocketTester(object):
    """The Socket tester class"""

    def __init__(self):
        self.prompt_base = 'Socket ({}) >>> '
        self.prompt = self.prompt_base.format(None)
        self.ip_port = None
        self.noauto = False
        self.name = None
        self.commands = None
        self.codenames = None

    def main(self, line=None):  # pylint: disable=too-many-branches
        """Main method"""
        if colorama is not None:
            colorama.init()

        if readline is not None:
            readline.parse_and_bind('tab: complete')
            readline.set_completer(SocketCompleter().complete)

        clear()
        print(WELCOME)

        while True:
            if line == None or line == '':
                pass
            elif line in ['quit', 'exit']:
                break
            elif line == 'help':
                self.help_()
            elif line.startswith('set '):
                self.set_(line.split('set ')[1])
                readline.set_completer(SocketCompleter(self.commands).complete)
            elif line.startswith('set_noauto '):
                self.set_(line.split('set_noauto ')[1], True)
            elif line == 'unset':
                self.unset()
            else:
                try:
                    self.forward_socket_command(line)
                except SocketTimeout:
                    message = 'Got timeout on command. Most likely there is '\
                              'no socket on {}:{}'.format(*self.ip_port)
                    message = '\n'.join(textwrap.wrap(message, 80))
                    print(ansi_color(message, ['bright', 'red']))
                    self.unset()
                except socket.gaierror:
                    message = 'Found no host at: {}'.format(self.ip_port[0])
                    print(ansi_color(message, ['bright', 'red']))
                    self.unset()

            # Get new line
            try:
                line = raw_input(self.prompt)
            except EOFError:
                line = 'quit'

        if colorama is not None:
            colorama.deinit()
        print('')

    def help_(self):
        """Print out the help"""
        clear()
        print(HELP_BASE)
        self.print_commands_and_codenames()

    def set_(self, ip_port, noauto=False):
        """Set ip address and port"""
        if not ':' in ip_port:
            message = 'The argument to set should be formatted as hostname:port'
            print(ansi_color(message, ['bright', 'red']))
            self.unset()
            return
        self.ip_port = ip_port.split(':')
        try:
            self.ip_port[1] = int(self.ip_port[1])
        except ValueError:
            message = 'The port argument "{}" is not cannot be converted to int'
            print(ansi_color(message.format(self.ip_port[1]), ['bright', 'red']))
            self.unset()
            return
        self.ip_port = tuple(self.ip_port)
        self.noauto = noauto
        print('Connected to: {}\n'.format(
            ansi_color('{}:{}'.format(*self.ip_port), ['bright', 'blue'])
        ))
        if not noauto:
            try:
                self.name, self.commands, self.codenames = \
                    commands_and_codenames(self.ip_port)
            except SocketTimeout:
                message = 'Got timeout on asking for name, commands and '\
                          'codenames. Most likely there is no socket on '\
                          '{}'.format(ip_port)
                message = '\n'.join(textwrap.wrap(message, 80))
                print(ansi_color(message, ['bright', 'red']))
                self.unset()
                return
            except socket.gaierror:
                message = 'Found no host at: {}'.format(self.ip_port[0])
                print(ansi_color(message, ['bright', 'red']))
                self.unset()
                return
        if self.name:
            print('The name of the socket is: {}\n'.format(
                ansi_color(self.name, ['bright', 'blue'])
            ))

        self.print_commands_and_codenames()

        self.prompt = self.prompt_base.format(ip_port)

    def unset(self):
        """Unset the ip port"""
        self.prompt = self.prompt_base.format(None)
        self.ip_port = None
        self.noauto = False
        self.name = None
        self.commands = None
        self.codenames = None

    def forward_socket_command(self, line, timeout=1):
        """Forward a socket command"""
        if self.ip_port is None:
            print('Unknown command: {}'.format(line))
            return

        SOCK.sendto(line, self.ip_port)
        ready = select.select([SOCK], [], [], timeout)
        if ready[0]:
            recv = SOCK.recv(65535)
        else:
            raise SocketTimeout()
        if 'json' in line or line in ['status']:
            try:
                recv = json.loads(recv)
            except ValueError:
                pass
        pprint(recv)

    def print_commands_and_codenames(self):
        """Print commands and codenames"""
        if self.commands:
            print('{0} {1} {0}\n'.format(
                ansi_color('==', ['bright', 'cyan']),
                ansi_color('Known commands', ['bright', 'magenta']),
            ))
            for command in self.commands:
                print(' * {}'.format(
                    ansi_color(command, ['bright', 'green'])
                ))
            print()
        if self.codenames:
            print('{0} {1} {0}\n'.format(
                ansi_color('==', ['bright', 'cyan']),
                ansi_color('Known codenames:', ['bright', 'magenta']),
            ))
            for codename in self.codenames:
                print(' * {}'.format(
                    ansi_color(codename, ['bright', 'green'])
                ))
            print()


def main():
    """Main function"""
    socket_tester = SocketTester()
    if len(sys.argv) > 1:
        line = ' '.join(sys.argv[1:])
    else:
        line = None

    socket_tester.main(line)


if __name__ == '__main__':
    main()
