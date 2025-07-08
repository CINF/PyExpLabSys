import os
import sys
import time
import pickle
import socket
import pathlib
import threading

import pexpect
import numpy as np
from icecream import ic

from nptdms import TdmsWriter, ChannelObject

from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

HOSTNAME = socket.gethostname()
machine_path = pathlib.Path.home() / 'machines' / HOSTNAME
sys.path.append(str(machine_path))


class MCSRunner:
    def __init__(self):
        threading.Thread.__init__(self)

        self.mcs = None  # Set by _init_mcs6a
        self.starts = 0
        self.measurement_running = False

        self.machine_path = machine_path
        self.running = True
        self.pullsocket = DateDataPullSocket(
            'tof-pull', ['total_count', 'starts'], timeouts=[600, 600]
        )
        self.pullsocket.start()
        self.pushsocket = DataPushSocket('tof-push', action='enqueue')
        self.pushsocket.start()
        # self._init_mcs6a()
        # self._init_measurement()

    def _init_mcs6a(self):
        self.mcs = pexpect.spawn('./testmcs6a')
        # Allow time for testmcs6a to start
        time.sleep(4)

    def _init_measurement(self):
        self._init_mcs6a()
        time.sleep(0.5)
        self.pullsocket.set_point_now('total_count', 0)
        self.pullsocket.set_point_now('starts', 0)

        # Length of spectrum is also available in the configuration data at the top
        # of each datafile
        # Time step is 0.0004micro seconds
        self.spectrum = np.zeros(135360)
        self.measurement_running = False
        self.starts = 0

    def _update_data(self):
        with open(self.machine_path / 'data.p', 'wb') as f:
            pickle.dump(self.spectrum, f)  # serialize the list
        with TdmsWriter(self.machine_path / 'data.tdms') as tdms_writer:
            channel = ChannelObject('group name', 'channel name', self.spectrum)
            tdms_writer.write_segment([channel])

    def _read_data_file(self):
        try:
            datafile = open('TEST.mpa', 'r')
            lines = datafile.readlines()
            datafile.close()
            os.remove('TEST.mpa')
        except FileNotFoundError:
            print('Did not find TEST.mpa - skipping the measurement')
            self.end_measurement()
            self.measurement_running = True
            self._init_mcs6a()
            return -1

        # Configuration lines are currently not actually used
        configuration_lines = []
        data_lines = []

        starts = 0
        data_started = False
        for raw_line in lines:
            line = raw_line.strip()
            if 'TDAT1' in line:
                break
            if data_started:
                data_lines.append(int(line))
            else:
                configuration_lines.append(line)
                if 'STARTS' in line:
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
        ic(self.starts, total_count)
        return total_count

    def _run_command(self, command):
        self.mcs.sendline(command)

    def _perform_single_measurement(self, iteration_time):
        print('Perform a measurement for {}s'.format(iteration_time))
        self._run_command('e')
        # time.sleep(0.2)
        time.sleep(1.0)
        self._run_command('s')
        time.sleep(iteration_time)
        self._run_command('h')
        # time.sleep(0.3)
        time.sleep(1.0)
        # Save the file
        self._run_command('t')
        # time.sleep(0.3)
        time.sleep(1.0)

    def measure(self, iterations, iteration_time=15):
        if self.measurement_running:
            return False
        self._init_mcs6a()
        self.measurement_running = True
        self._init_measurement()
        while self.starts < iterations:
            self._perform_single_measurement(iteration_time)
            self._read_data_file()
        self.end_measurement()

    def end_measurement(self):
        self._run_command('h')
        time.sleep(1)
        self._run_command('e')
        time.sleep(1)
        self._run_command('q')
        time.sleep(1)
        self.measurement_running = False
        self.mcs = None

    def run(self):
        while self.running:
            time.sleep(1)
            print(self.starts)
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                qsize = self.pushsocket.queue.qsize()

                if element['cmd'] == 'quit':
                    self._quit()
                    self.running = False

                if element['cmd'] == 'start_measurement':
                    if self.measurement_running:
                        continue
                    sweeps = element.get('sweeps', -1)
                    iteration_time = element.get('iteration_time', 5)
                    self.measure(sweeps, iteration_time)


if __name__ == '__main__':
    mcs = MCSRunner()
    mcs.run()

    # mcs.perform_a_measurement(10)
    # print(mcs._read_data_file())

    # mcs.perform_a_measurement(10)
    # print(mcs._read_data_file())

    # mcs.perform_a_measurement(10)
    # print(mcs._read_data_file())

    # mcs.perform_a_measurement(10)
    # print(mcs._read_data_file())

    # mcs.quit()
