"""My example stepped program"""

from __future__ import print_function

# Import builtins
import sys
import socket
import json
from time import time, sleep
from threading import Thread
from functools import partial
from queue import Queue
import argparse
from pprint import pformat

# Import third party
from numpy import isclose
from yaml import load
from PyQt4.QtGui import QApplication

# Import from PyExpLabSys
from PyExpLabSys.apps.stepped_program_runner.stepped_program_runner import SteppedProgramRunner
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.utilities import get_logger
LOG = None

import credentials

# Setup communication with the power supply server
HOST, PORT = "localhost", 8500
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
def _send_command(output, command, arg=None):
    """Send a command to the power supply server
    
    Args:
        output (str): The output number in a string; either 1 or 2
        command (str): The command/name of the method to call on the power
            supply object
        arg (object): The argument to the command/method
    """
    data_to_send = {'command': command, 'output': output}
    if arg is not None:
        data_to_send['arg'] = arg
    formatted_command = b'json_wn#' + json.dumps(data_to_send).encode('utf-8')

    sock.sendto(formatted_command, (HOST, PORT))
    received = sock.recv(1024).decode('utf-8')

    if received.startswith('ERROR:'):
        raise PowerSupplyComException(received)

    # The return values starts with RET#
    return json.loads(received[4:])


class PowerSupplyComException(Exception):
    pass


class ConstantValueStep(object):
    """A constant value step"""

    def __init__(self, duration, value, probe_interval=0.1):
        self.duration = duration
        self.value = value
        self.probe_interval = probe_interval
        # For interbal bookkeeping of the time
        self._start = None
        self._elapsed = 0.0

    def __str__(self):
        return 'ContantStep(duration={}, value={}, probe_interval={})'.format(
            self.duration, self.value, self.probe_interval,
        )

    def start(self):
        """Start this step"""
        self._start = time()

    def stop(self):
        """Stop the step"""
        self._elapsed = time() - self._start
        self._start = None

    def elapsed(self):
        """Return the elapsed time"""
        if self._start is None:
            return self._elapsed
        else:
            return time() - self._start

    def remaining(self):
        """Return remaining time"""
        return self.duration - self.elapsed()


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


def f2(number):
    return '{:.2f}'.format(number)

def f3(number):
    return '{:.3f}'.format(number)

class MyProgram(Thread):
    """My fancy program"""

    def __init__(self, args):
        super(MyProgram, self).__init__()

        # Form channel_id e.g: A1
        self.channel_id = args.power_supply + args.output

        ### Required by the stepped program runner
        # Accepted capabilities are: can_edit_line, can_play,
        # can_stop, can_quit
        self.capabilities = ('can_stop', 'can_start')
        self.status_fields = (
            # codename, Headline, formatter
            (self.channel_id + '_voltage', 'Voltage', f3),
            (self.channel_id + '_voltage_setpoint', 'Voltage Setpoint', f3),
            (self.channel_id + '_current', 'Current', f3),
            ('elapsed', 'Step elapsed', None),
            ('remaining', 'Step remaining', f2),
            ('iteration_time', 'Iteration time', f2),
        )
        # Queue for GUI updates
        self.message_queue = Queue()
        # The GUI also looks in self.config, see below

        ### Normal program
        # Setup my program
        with open(args.program_file) as file_:
            self.config, self.steps = parse_ramp(file_)
        # The GUI will look for keys: program_title in config
        self.say('Using power supply channel: ' + self.channel_id)
        self.say('Loaded with config:\n' + pformat(self.config))
        self.active_step = 0
        self.send_steps()

        # Base for the status
        self.status = {'elapsed': 0}

        # General variables
        self.stop = False
        self.ok_to_start = False

        # Setup power supply
        # Create a partial function with the output substitued in
        self.send_command = partial(_send_command, args.output)
        self.power_supply_on_off(True, self.config['maxcurrent'])
        # Power supply commands, must match order with self.codenames
        self.power_supply_commands = (
            'read_actual_current', 'read_actual_voltage', 'read_set_voltage'
        )

        # Setup dataset saver and live socket
        self.codenames = [self.channel_id + id_ for id_ in
                          ('_current', '_voltage', '_voltage_setpoint')]
        self.live_socket = LiveSocket(
            'H2O2_proactive_' + self.channel_id, self.codenames,
            no_internal_data_pull_socket=True
        )
        self.live_socket.reset(self.codenames)
        self.live_socket.start()

        self.data_set_saver = DataSetSaver(
            credentials.measurements, credentials.xy_values,
            username=credentials.username, password=credentials.password
        )
        self.data_set_saver.start()

    def command(self, command, args_str):
        """Process commands from the GUI"""
        if command == 'stop':  # stop is sent on quit
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
        """The MAIN run method"""
        # Wait for start
        while not self.ok_to_start:
            if self.stop:
                self.power_supply_on_off(False)
                return
            sleep(0.1)

        # Start
        self.setup_data_set_saver()

        # Run the MAIN measurement loop
        # (This is where most of the time is spent)
        self.main_measure()

        # Shutdown powersupply and livesocket
        self.stop_everything()

        sleep(0.1)
        self.say("I have stopped")

    def setup_data_set_saver(self):
        """Setup the data set saver"""
        sql_time = CustomColumn(time(), 'FROM_UNIXTIME(%s)')
        for codename in self.codenames:
            metadata = {
                'time': sql_time, 'comment': self.config['comment'],
                'label': codename[3:], 'type': 1,
                'power_supply_channel': self.channel_id,
            }
            self.data_set_saver.add_measurement(codename, metadata)

    def main_measure(self):
        """The main measurement loop"""
        # Initial setup
        program_start = time()
        last_set_voltage = None
        last_time = time()
        iteration_time = 'N/A'

        self.say('I started on step 0')
        for self.active_step, current_step in enumerate(self.steps):
            # Also give the step an instance name (for steps list)
            if self.active_step > 0:
                self.say('Switched to step: {}'.format(self.active_step))
            self.send_steps()
            current_step.start()

            # While the step hasn't completed yet
            while current_step.elapsed() < current_step.duration:
                # Check if we should stop
                if self.stop:
                    self.say('I have been asked to stop')
                    return

                iteration_start = now = time()
                # Calculate the time for one iteration and update times in status
                iteration_time = now - last_time
                last_time = now
                self.status.update({
                    'elapsed': current_step.elapsed(),
                    'remaining': current_step.remaining(),
                    'iteration_time': iteration_time,
                })
    
                # Ask the power supply to set a new voltage if needed
                current_value = current_step.value
                if current_value != last_set_voltage:
                    self.send_command('set_voltage', current_value)
                    last_set_voltage = current_value
    
                # Read value from the power supply
                self._read_values_from_power_supply(program_start)
                self.send_status()
    
                # Calculate time to sleep to use the proper probe interval
                time_to_sleep = current_step.probe_interval - (time() - iteration_start)
                if time_to_sleep > 0:
                    sleep(time_to_sleep)

        # For loop over steps ended
        self.say('Stepped program completed')


    def _read_values_from_power_supply(self, program_start):
        """Read all required values from the power supply (used only from run)"""
        elapsed_all_steps = sum(step.elapsed() for step in self.steps)
        for command, codename in zip(self.power_supply_commands, self.codenames):
            # Get a value for the current command
            value = self.send_command(command)
            if command == 'read_set_voltage':
                value = float(value.strip().split(' ')[1])
            # Set/save it on the live_socket, database and in the GUI
            point = (elapsed_all_steps, value)
            self.live_socket.set_point(codename, point)
            self.data_set_saver.save_point(codename, point)
            self.status[codename] = value

    def stop_everything(self):
        """Stop power supply and live socket"""
        self.power_supply_on_off(False) 
        self.live_socket.stop()
        self.data_set_saver.stop()

    def power_supply_on_off(self, state, current_limit=0.0):
        """Set power supply on off"""
        # Set voltage to 0
        LOG.debug('Stopping everything. Set voltage to 0.0')
        self.send_command('set_voltage', 0.0)
        start = time()
        while self.send_command('read_actual_voltage') > 1E-2:
            # Give it a second to set
            if time() - start > 3:
                LOG.error('Unable to set voltage to 0')
                if state:
                    raise RuntimeError('Unable to set voltage to 0')
                else:
                    self.say('Unable to set voltage to 0')


        # Set current limit
        self.send_command('set_current_limit', current_limit)
        read_current_limit = float(
            self.send_command('read_current_limit').strip().split(' ')[1]
        )
        if not isclose(read_current_limit, current_limit):
            raise RuntimeError('Unable to set current limit')

        # Set state
        self.send_command('output_status', state)
        read_state = self.send_command('read_output_status').strip() == '1'
        if not read_state is state:
            raise RuntimeError('Could not set output state')



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
    
    global LOG
    LOG = get_logger(
        'STACK TESTER ' + args.power_supply + args.output,
        level='debug', file_log=True,  terminal_log=False,
        file_name='stack_tester_' + args.power_supply + args.output + '.log'
    )

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

try:
    main()
except Exception as exc:
    LOG.exception("Catched exception at the outer layer")
    if isinstance(exc, ConnectionResetError):
        LOG.info('Unable to connect to the power supply server. '
                 'Did you rememver to start it?')
    raise
