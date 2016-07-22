"""My example stepped program"""

from __future__ import print_function

import sys
from time import time, sleep
from threading import Thread
try:
    from queue import Queue
except ImportError:
    from Queue import Queue
import argparse
from pprint import pformat

from yaml import load, dump
from PyQt4.QtGui import QApplication

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


def parse_ramp(file_):
    """Parse the ramp file"""
    # Eveything in the steps file is config, except the step list
    # which is extracted below
    config = load(file_)

    # Load steps
    steps = []
    step_definitions = config.pop('steps')
    for step_definition in step_definitions:
        type_  = step_definition.pop('type')
        if type_ == 'ConstantValueStep':
            steps.append(ConstantValueStep(**step_definition))

    return config, steps


class MyProgram(Thread):
    """My fancy program"""

    def __init__(self, args):
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
        # The GUI also looks in self.config, see below

        ### Normal program
        # Setup my program
        with open(args.program_file) as file_:
            self.config, self.steps = parse_ramp(file_)
        # The GUI will look for keys: program_title in config
        self.say('Loaded with config:\n' + pformat(self.config))

        self.active_step = 0
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
    # Parse arguments
    parser = argparse.ArgumentParser(description=('Runs a stepped power supply program on '
                                                  'a specified power supply and channel'))
    parser.add_argument('power_supply', choices=('A'),
                        help='The capital lette of a power supply e.g. A')
    parser.add_argument('output', choices=('1', '2'),
                        help='The output number on that power supply. Must be 1 or 2')
    parser.add_argument('program_file', help="The file that contains the ramp")
    args = parser.parse_args()

    # Init program
    my_program = MyProgram(args)
    my_program.start()

    # Appearently, it is better to defined app at the module level for
    # clean up: http://stackoverflow.com/questions/27131294/
    # error-qobjectstarttimer-qtimer-can-only-be-used-with-threads-started-with-qt
    global app
    app = QApplication(sys.argv)
    SteppedProgramRunner(my_program)
    sys.exit(app.exec_())


main()
