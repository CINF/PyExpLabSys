import time
import pickle
import pexpect
import threading

import numpy as np

from nptdms import TdmsWriter, ChannelObject

from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import DateDataPullSocket


class MCSRunner():
    def __init__(self):
        threading.Thread.__init__(self)
        self.mcs = pexpect.spawn('./testmcs6a')
        # Allow time for testmcs6a to start
        time.sleep(4)

        self.running = True
        self.pullsocket = DateDataPullSocket(
            'tof-pull', ['total_count', 'starts'], timeouts=[600, 600]
        )
        self.pullsocket.start()
        self.pushsocket = DataPushSocket('tof-push', action='enqueue')
        self.pushsocket.start()
        self._init_measurement()

    def _init_measurement(self):
        self.pullsocket.set_point_now('total_count', 0)
        self.pullsocket.set_point_now('starts', 0)

        # Length of spectrum is also available in the configuration data at the top
        # of each datafile
        # Time step is 0.0004micro seconds
        self.spectrum = np.zeros(135360)
        self.measurement_running = False
        self.starts = 0

    def _update_data(self):
        with open('data.p', 'wb') as f:
            pickle.dump(self.spectrum, f) # serialize the list
        with TdmsWriter("data.tdms") as tdms_writer:
            channel = ChannelObject('group name', 'channel name', self.spectrum)
            tdms_writer.write_segment([channel])

    def _read_data_file(self):
        datafile = open('TEST.mpa', 'r')
        lines = datafile.readlines()

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

        assert starts > 0
        self.starts += starts
        total_count = sum(self.spectrum)
        self.pullsocket.set_point_now('total_count', total_count)
        self.pullsocket.set_point_now('starts', self.starts)
        return total_count

    def _run_command(self, command):
        self.mcs.sendline(command)

    def _perform_single_measurement(self, iteration_time):
        print('Perform a measurement for {}s'.format(iteration_time))
        self._run_command('e')
        time.sleep(0.2)
        self._run_command('s')
        time.sleep(iteration_time)
        self._run_command('h')
        time.sleep(0.2)
        # Save the file
        self._run_command('t')
        time.sleep(0.2)

    def measure(self, iterations, iteration_time=5):
        if self.measurement_running:
            return False
        self.measurement_running = True
        self._init_measurement()
        while self.starts < iterations:
            self._perform_single_measurement(iteration_time)
            self._read_data_file()
        self.measurement_running = False

    def _quit(self):
        self._run_command('q')

    def run(self):
        while self.running:
            time.sleep(0.5)
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
