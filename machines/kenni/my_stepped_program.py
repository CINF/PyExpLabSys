

import sys
from PyQt4.QtGui import (QApplication)

from PyExpLabSys.apps.stepped_program_runner import SteppedProgramRunner


class ConstantStep(object):
    def __init__(self, time, value):
        self.time = time
        self.value = value


class MyProgram(object):
    """My fancy program"""


    def __init__(self):
        ### Required by the stepped program runner
        # Accepted capabilities are: can_remove_line, can_add_line
        #   can_edit_line, can_play, can_stop, can_quit
        self.capabilities = ('can_quit')
        self.can_remove_line = False
        self.can_add_line = False
        self.can_edit_lines = False
        # An edit is a list of properties that can be set for a line
        # keys are the integer place in program (starting from 0)
        self.edits = {}

        ### Normal program
        # Set my program
        self.lines = [
            ConstantStep(2, 10.),
            ConstantStep(3, 4.),
        ]

        for index, line in enumerate(self.lines):
            self.edits[index] = (('time', int), ('value', float))

    def command(self, command, args_str):
        """Process commands, has to implement quit"""
        if command == 'quit':
            return
        


def main():
    app = QApplication(sys.argv)
    my_program = MyProgram()
    main_window = SteppedProgramRunner(my_program)
    sys.exit(app.exec_())


main()
