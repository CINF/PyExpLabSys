"""My example stepped program"""

from __future__ import print_function

import sys
from time import time, sleep
from threading import Thread
try:
    from queue import Queue
except ImportError:
    from Queue import Queue

from PyQt4.QtGui import (QApplication)
from PyExpLabSys.apps.stepped_program_runner.stepped_program_runner import SteppedProgramRunner

class ConstantValueStep(object):
    """A constant value step"""

    def __init__(self, duration, value, probe_interval=0.1):
        self.duration = duration
        self.value = value
        self.probe_interval = probe_interval

    def __str__(self):
        return 'ContantStep(duration={}, value={})'.format(
            self.duration, self.value
        )


class MyProgram(Thread):
    """My fancy program"""

    def __init__(self):
        super(MyProgram, self).__init__()

        ### Required by the stepped program runner
        # Accepted capabilities are: can_edit_line, can_play,
        # can_stop, can_quit
        self.capabilities = ('can_stop', 'can_start')
        self.status_fields = (
            # codename, Headline
            ('bias', 'Bias'),
            ('current', 'Current'),
            ('elapsed', 'Step elapsed'),
            ('remaining', 'Step remaining'),
        )
        # Queue for GUI updates
        self.message_queue = Queue()

        ### Normal program
        # Set my program
        self.active_step = 0
        self.steps = [
            ConstantValueStep(2, 10.),
            ConstantValueStep(3, 4.),
        ]
        self.send_steps()

        # Base for the status
        self.status = {
            'bias': 0,
            'current': 0,
            'elapsed': 'N/A',
            'remaining': 'N/A',
        }

        # Generic variables
        self.stop = False
        self.ok_to_start = False
        self.status = {}

        self.daemon = True  # FIXME Remove

    def command(self, command, args_str):
        """Process commands, has to implement quit"""
        if command == 'stop':
            self.stop = True
        elif command == 'start':
            self.ok_to_start = True

    def send_status(self):
        """Send the status to the GUI"""
        self.message_queue.put(('status', self.status.copy()))

    def send_steps(self):
        """Send the steps list to the GUI"""
        steps = [(index == self.active_step, str(step))
                 for index, step in enumerate(self.steps)]
        self.message_queue.put(('steps', steps))

    def say(self, text):
        """Send a ordinary text message to the gui"""
        self.message_queue.put(('message', text))

    def run(self):
        """The main run method"""
        # Wait for start
        while not self.ok_to_start:
            if self.stop:
                return
            sleep(0.1)
        self.say('I started')
        # Initial setup
        current_start = time()
        current_step = self.steps[self.active_step]
        self.status['bias'] = current_step.value
        self.status['current'] = current_step.value
        self.send_status()
        while not self.stop:
            # If we are done with the step
            if time() - current_start > current_step.duration:
                self.active_step += 1
                try:
                    current_step = self.steps[self.active_step]
                    current_start = time()
                    self.status['bias'] = current_step.value
                    self.status['current'] = current_step.value
                    self.send_steps()
                    self.send_status()
                    self.say('Switched to step: {}'.format(self.active_step))
                except IndexError:
                    # We are done
                    self.say('Stepped program completed')
                    break

            self.status['elapsed'] = time() - current_start
            self.status['remaining'] = current_step.duration - self.status['elapsed']
            self.send_status()

            sleep(0.1)
        else:
            self.say('I have been asked to stop')
        self.say("I have stopped")


def main():
    """Main function"""
    my_program = MyProgram()
    my_program.start()
    # Appearently, it is better to defined app at the module level for
    # clean up: http://stackoverflow.com/questions/27131294/
    # error-qobjectstarttimer-qtimer-can-only-be-used-with-threads-started-with-qt
    global app
    app = QApplication(sys.argv)
    SteppedProgramRunner(my_program)
    sys.exit(app.exec_())


main()
