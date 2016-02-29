#!/usr/bin/env python

"""Python version of the cowsay program"""

from __future__ import print_function
from textwrap import wrap
import sys
from StringIO import StringIO


COWS = {
    'cow':
r"""
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||

""".lstrip('\n'),
    'tux':
r"""
    \
        .--.
       |o_o |
       |:_/ |
      //   \ \
     (|     | )
    /'\_   _/`\
    \___)=(___/
""".lstrip('\n')
}


def list_cows():
    """List the available cow avatars"""
    return COWS.keys()


class Cowsay(object):
    """Primitive cowsay class"""

    def __init__(self, cow='cow', width=40):
        """Initialize the internal variables.

        Args:
            cow (str): The cow to use. Use the module functions list_cows to
                see which avatars can be used
        """
        try:
            self.cow = COWS[cow]
        except KeyError:
            message = 'Cow \'{}\' is unknown. Only {} are allowed'\
                .format(cow, list(COWS.keys()))
            raise ValueError(message)

        self.width = width

        self.out = sys.stdout

    def say(self, text):
        """Make the cow say something"""
        wrapped_lines = wrap(text, self.width)
        text_width = max(len(line) for line in wrapped_lines)
        self.out.write('  ' + '_' * text_width + '\n',)
        template = '{{}} {{: <{}}} {{}}\n'.format(text_width)
        if len(wrapped_lines) == 1:
            self.out.write(template.format('<', wrapped_lines[0], '>'))
        else:
            for line_num, line in enumerate(wrapped_lines):
                if line_num == 0:
                    left, right = '/', '\\'
                elif line_num == len(wrapped_lines) - 1:
                    left, right = '\\', '/'
                else:
                    left, right = '|', '|'
                self.out.write(template.format(left, line, right))

        self.out.write('  ' + '-' * text_width + '\n')
        self.out.write(self.cow + '\n')

    def say_get_string(self, text):
        """Get the cow output as a string"""
        sio = StringIO()
        self.out = sio
        self.say(text)
        self.out = sys.stdout
        sio.seek(0)
        return sio.read()


if __name__ == '__main__':
    COW = Cowsay(cow='tux')
    TESTCOW = COW.say_get_string("Live long and prosper")
    print(TESTCOW)
