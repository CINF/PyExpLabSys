

import sys

from time import time, sleep
from threading import Thread

from PyQt4.QtGui import (QApplication)
from PyExpLabSys.apps.stepped_program_runner import SteppedProgramRunner

class ConstantStep(object):
    def __init__(self, time, value, probe_interval=0.1):
        self.time = time
        self.value = value
        self.probe_interval = probe_interval

    def __str__(self):
        return 'ContantStep(time={}, value={})'.format(self.time, self.value)


class MyProgram(Thread):
    """My fancy program"""


    def __init__(self):
        super(MyProgram, self).__init__()

        ### Required by the stepped program runner
        # Accepted capabilities are: can_edit_line, can_play,
        # can_stop, can_quit
        self.capabilities = ('can_quit')
        self.status_fields = (
            ('bias', 'Bias'),
            ('current', 'Current'),
            ('elapsed', 'Step elapsed'),
            ('remaining', 'Step remaining'),
        )

        ### Normal program
        # Set my program
        self.steps = [
            ConstantStep(2, 10.),
            ConstantStep(3, 4.),
        ]

        self.stop = False
        self.active_step = 0
        self.status = {}

    def command(self, command, args_str):
        """Process commands, has to implement quit"""
        if command == 'quit':
            self.stop = True
            #while self.isRunn

    def get_status(self):
        return {
            'bias': 8,
            'current': 2,
            'elapsed': 99,
            'remaining': 99,
        }

    def get_steps(self):
        """Return a list of steps and whether it is active"""
        return [(index==self.active_step, str(step))
                for index, step in enumerate(self.steps)]

    def run(self):
        """The main run method"""
        current_start = time()
        active_step_number = 0
        current_step = self.steps[0]
        self.status['bias'] = current_step.value
        self.status['current'] = current_step.value
        while not self.stop:
            # If we are done with the step
            if time() - current_start > current_step.time:
                active_step_number += 1
                try:
                    current_step = self.steps[active_step_number]
                    current_start = time()
                    self.status['bias'] = current_step.value
                    self.status['current'] = current_step.value
                except IndexError:
                    # We are done
                    break

            self.status['elapsed'] = time() - current_start
            self.status['remaining'] = current_step.time - self.status['elapsed']
            print(current_step, self.status)

            sleep(0.1)
        print('done')

            
                
                
            
            
            
            
        


def main():
    app = QApplication(sys.argv)
    my_program = MyProgram()
    my_program.start()
    main_window = SteppedProgramRunner(my_program)
    sys.exit(app.exec_())


main()
