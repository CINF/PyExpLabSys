import os
import sys
import time
import pickle
import socket
import pathlib
import threading
import subprocess

import numpy as np
from icecream import ic

from pynput import mouse, keyboard

from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

HOSTNAME = socket.gethostname()
machine_path = pathlib.Path.home() / 'machines' / HOSTNAME
sys.path.append(str(machine_path))


def focus_mpant():
    subprocess.run(["xdotool", "search", "--name", "MPANT", "windowactivate"])


class MCSRunner:
    def __init__(self):
        threading.Thread.__init__(self)
        self.kc = keyboard.Controller()

        self.wanted_iterations = 0
        self.starts = 0
        self.measurement_running = False

        self.machine_path = machine_path
        self.running = True
        self.pullsocket = DateDataPullSocket(
            'tof-pull', ['total_count', 'starts', 'finished'], timeouts=[600, 600, 600]
        )
        self.pullsocket.start()
        self.pushsocket = DataPushSocket('tof-push', action='enqueue')
        self.pushsocket.start()
        self._init_measurement()
        self.mark_counter = -1

    def _get_marker(self):
        """Get spinning marker"""
        self.mark_counter += 1
        if self.mark_counter == 0:
            return '-'
        if self.mark_counter == 1:
            return '\\'
        if self.mark_counter == 2:
            return '|'
        if self.mark_counter == 3:
            self.mark_counter = -1
            return '/'

    def _init_measurement(self):
        self.pullsocket.set_point_now('total_count', 0)
        self.pullsocket.set_point_now('starts', 0)
        self.pullsocket.set_point_now('finished', 0)

        # Length of spectrum is also available in the configuration data at the top
        # of each datafile
        # Time step is 0.0004micro seconds
        self.spectrum = np.zeros(135360)
        self.measurement_running = False
        self.starts = 0
        self.last_measurement = time.time()

    def _update_data(self):
        with open(self.machine_path / 'data.p', 'wb') as f:
            pickle.dump(self.spectrum, f)  # serialize the list

    def _read_data_file(self):
        t0 = time.time()
        datafile = pathlib.Path('/home/roje/.wine/drive_c/MCS6Ax64') / 'TEST.mpa'
        if datafile.exists():
            lines = datafile.read_text()
            datafile.unlink()
        else:
            print('Did not find TEST.mpa - skipping the measurement')
            self.measurement_running = True
            return -1

        # Configuration lines are currently not actually used
        configuration_lines = []
        data_lines = []

        starts = 0
        data_started = False
        for raw_line in lines.split('\n'):
            line = raw_line.strip()
            if 'TDAT1' in line:
                break
            if data_started:
                if line:
                    data_lines.append(int(line))
            else:
                configuration_lines.append(line)
                # if 'STARTS' in line:
                #    starts = int(line[8:])
                if 'SWEEPS' in line:
                    starts = int(line[8:])
            if 'TDAT0' in line:
                data_started = True

        data = np.array(data_lines)
        assert len(data) == len(self.spectrum)
        self.spectrum += data
        self._update_data()

        if not starts > 0:
            # File exists but no measurements has been takens
            ic('No starts in file!')
            return -1
        self.starts += starts
        msg = 'Starts in this file: {}. Total starts: {}'.format(starts, self.starts)
        print(msg)
        total_count = sum(self.spectrum)
        msg = 'Counts in this file: {}. Total counts: {}'.format(sum(data), total_count)
        print(msg)
        self.pullsocket.set_point_now('total_count', total_count)
        self.pullsocket.set_point_now('starts', self.starts)
        self.pullsocket.set_point_now('finished', 0)
        ic(self.starts, total_count)
        print('parsed file in {:.3}s'.format(time.time() - t0))  ###
        return total_count

    def _perform_single_measurement(self, iteration_time, debug=False):
        debug_scale = 1
        if debug:
            debug_scale = 10

        # TODO: THIS CAN BE DONE WITH xdotool -
        # actually it should even be possible to direct
        # keystrokes directly to the window without needing
        # to focus it.
        # Use xdotool to focus MPANT - MSC6A window
        focus_mpant()
        print('Perform a measurement for {}s'.format(iteration_time))
        # Action -> Erase
        with self.kc.pressed(keyboard.Key.alt):
            self.kc.press('a')
            self.kc.release('a')
        time.sleep(0.1 * debug_scale)
        self.kc.press('e')
        self.kc.release('e')
        # Action -> Start
        with self.kc.pressed(keyboard.Key.alt):
            self.kc.press('a')
            self.kc.release('a')
        time.sleep(0.1 * debug_scale)
        self.kc.press('s')
        self.kc.release('s')

        # Wait for measurement
        time.sleep(iteration_time)

        # Use xdotool to focus MPANT - MSC6A window
        focus_mpant()
        print('End measurement')
        # Action -> Halt
        with self.kc.pressed(keyboard.Key.alt):
            self.kc.press('a')
            self.kc.release('a')
        time.sleep(0.1 * debug_scale)
        self.kc.press('h')
        self.kc.release('h')
        time.sleep(0.5 * debug_scale)

        print('Save data')
        # File -> Save MPA As
        with self.kc.pressed(keyboard.Key.alt):
            self.kc.press('f')
            self.kc.release('f')
        self.kc.press('m')
        self.kc.release('m')

        time.sleep(0.25 * debug_scale)
        # Accept default in dialogue box
        self.kc.press(keyboard.Key.enter)
        self.kc.release(keyboard.Key.enter)
        print('Done')

    def stop_current_measaurement(self):
        self.wanted_iterations = 0

    def measure_in_sweeps(self, iterations, iteration_time=15):
        self.wanted_iterations = iterations
        if self.measurement_running:
            return False
        self._init_measurement()
        self.measurement_running = True

        while self.starts < self.wanted_iterations:
            self._perform_single_measurement(iteration_time)
            self._read_data_file()
        self.pullsocket.set_point_now('finished', 1)
        self.measurement_running = False

    def measure_in_minutes(self, minutes=5, iteration_time=15):
        duration = minutes * 60  # duration in seconds
        if self.measurement_running:
            return False
        self._init_measurement()
        self.measurement_running = True

        measurement_start = time.time()
        while time.time() - measurement_start <= duration - iteration_time:
            self._perform_single_measurement(iteration_time)
            self._read_data_file()
        self.pullsocket.set_point_now('finished', 1)
        self.measurement_running = False

    def run(self):
        msg = '{} Starts: {}                        '
        while self.running:
            time.sleep(1)
            print(msg.format(self._get_marker(), self.starts), end='\r')
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                qsize = self.pushsocket.queue.qsize()

                if element['cmd'] == 'quit':
                    self._quit()
                    self.running = False

                if element['cmd'] == 'stop_measurement':
                    self.stop_current_measaurement()  # TODO: should not work since it is not threaded

                if element['cmd'] == 'start_measurement':
                    if self.measurement_running:
                        continue
                    sweeps = element.get('sweeps', -1)
                    duration = element.get('minutes', 0)
                    iteration_time = element.get('iteration_time', 5)
                    if duration > 0:
                        self.measure_in_minutes(duration, iteration_time)
                    else:
                        self.measure_in_sweeps(sweeps, iteration_time)


if __name__ == '__main__':
    mcs = MCSRunner()
    mcs.run()

    # time.sleep(5)

    # mcs._perform_single_measurement(5, debug=True)
    # print(mcs._read_data_file())

    # mcs.perform_a_measurement(10)
    # print(mcs._read_data_file())

    # mcs.perform_a_measurement(10)
    # print(mcs._read_data_file())

    # mcs.perform_a_measurement(10)
    # print(mcs._read_data_file())

    # mcs.quit()
