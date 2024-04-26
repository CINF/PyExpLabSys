import sys
import json
import time
import pickle
import socket
import pathlib

import numpy as np

from icecream import ic

from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn

HOSTNAME = socket.gethostname()
machine_path = pathlib.Path.home() / 'machines' / HOSTNAME
sys.path.append(str(machine_path))

import credentials  # pylint: disable=wrong-import-position, import-error


class Tof:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(0)
        self.expected_iterations = 0
        self.machine_path = machine_path

        self.data_set_saver = DataSetSaver(
            'measurements_tof', 'xy_values_tof', credentials.user, credentials.passwd
        )
        self.data_set_saver.start()

    def contact_external_pi(self, payload, hostname, port=9000):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(0)
        self.sock.sendto(payload.encode(), (hostname, port))
        time.sleep(0.02)
        recv = self.sock.recv(65535)
        # print('recv: ', recv)
        raw_reply = recv.decode('ascii')
        return raw_reply

    def _send_command(self, payload, port):
        if port == 8500:
            socket_command = 'json_wn#' + json.dumps(payload)
        else:
            socket_command = payload

        error = 0
        while error > -1:
            if error > 5:
                ic('We have a communication issue')
                time.sleep(0.5)
            try:
                self.sock.sendto(socket_command.encode(), ('127.0.0.1', port))
                time.sleep(0.02)
                recv = self.sock.recv(65535)
                error = -1
            except BlockingIOError:
                error += 1
                time.sleep(0.001)

        raw_reply = recv.decode('ascii')
        try:
            data = json.loads(raw_reply)
            value = data[1]
        except json.decoder.JSONDecodeError:
            value = raw_reply
        return value

    def _read_emission_rom_rasppi49(self):
        # todo: this does not need to be a separate function, but practical to test
        cmd = 'ionenergy#json'
        raw_reply = self.contact_external_pi(cmd, '10.54.7.49', 9000)
        data = json.loads(raw_reply)
        ionenergy = data[1]

        cmd = 'emission#json'
        raw_reply = self.contact_external_pi(cmd, '10.54.7.49', 9000)
        data = json.loads(raw_reply)
        emission = data[1]
        return ionenergy, emission

    def _read_ion_optics_from_rasppi74(self):
        cmd_list = [
            'lens_a',
            'lens_b',
            'lens_c',
            'lens_d',
            'lens_e',
            'focus',
            'extraction',
        ]
        optics_values = {}
        for cmd in cmd_list:
            raw_reply = self.contact_external_pi(cmd + '#json', '10.54.7.74', 9000)
            try:
                data = json.loads(raw_reply)
                optics_values[cmd] = float(data[1])
            except json.decoder.JSONDecodeError:
                print('Error reading {} from rasppi74!'.format(cmd))
                optics_values[cmd] = 0
        return optics_values

    def _read_voltages_from_rasppi74(self):
        # todo: this does not need to be a separate function, but practical to test
        # We do not need to block while we wait the 9 seconds
        # time.sleep(9)
        # rasppi74.fys.clients.local (10.54.7.74):
        cmd = 'read_voltages\r'
        items_raw = self.contact_external_pi(cmd, '10.54.7.74', 9696)
        print(items_raw)
        items = {}
        for item in items_raw.split(' '):
            if len(item) < 1:
                continue
            try:
                item_list = item.split(':')
                key = item_list[0]
                value = float(item_list[1])
                items[key] = value
            except IndexError:
                items[key] = 0
        return items

    def read_acq_status(self):
        cmd = 'starts#json'
        starts = self._send_command(cmd, 9000)
        try:
            starts = float(starts)
        except ValueError:
            starts = 0
        cmd = 'total_count#json'
        total_counts = self._send_command(cmd, 9000)
        try:
            total_counts = float(total_counts)
        except ValueError:
            total_counts = 0
        reply = {'starts': starts, 'total_counts': total_counts}
        return reply

    def start_measurement(self, iterations):
        self.expected_iterations = iterations

        # TODO: Pulse voltage should be configurable!
        self.contact_external_pi('start_tof_measurement 800', 'rasppi74', 9696)
        # TODO! Remember to also send the stop command!
        time.sleep(2)

        payload = {
            'cmd': 'start_measurement',
            'sweeps': iterations,
            'iteration_time': 5,
        }
        self._send_command(payload, 8500)
        return

    def are_we_done_yet(self):
        status = self.read_acq_status()
        done = status['starts'] >= self.expected_iterations
        return done

    def abort_measurement(self):
        # 'cmd': 'quit',
        payload = {
            'cmd': 'abort_sweep',
        }
        self._send_command(payload, 8500)
        return

    def create_measurement_entry(self, comment):
        tof_iterations = self.read_acq_status()['starts']

        ion_energy, emission = self._read_emission_rom_rasppi49()
        tof_voltages = self._read_voltages_from_rasppi74()
        optics_values = self._read_ion_optics_from_rasppi74()
        # tof_voltages['a2']: -0.00747876097266

        tof_pulse_voltage = 800  # todo: Currently hard codet

        metadata = {
            # Endtime, should this had been starttime?
            'Time': CustomColumn(time.time(), "FROM_UNIXTIME(%s)"),
            'type': 11,
            'comment': comment,
            'tof_iterations': tof_iterations,
            'tof_pulse_voltage': tof_pulse_voltage,
            'tof_liner_voltage': tof_voltages['liner'],
            'tof_lens_A': optics_values['lens_a'],
            'tof_lens_B': optics_values['lens_b'],
            'tof_lens_C': optics_values['lens_c'],
            'tof_lens_D': optics_values['lens_d'],
            'tof_lens_E': optics_values['lens_e'],
            'tof_ion_energy': ion_energy,
            'tof_R1_voltage': tof_voltages['r1'],
            'tof_R2_voltage': tof_voltages['r2'],
            'sem_voltage': tof_voltages['mcp'],
            # DEFLECTION!!!!! tof_voltages['deflection'],
            'tof_focus_voltage': tof_voltages['focus'],
            'tof_emission_current': emission,
            'emission_focus': optics_values['focus'],
            'emission_extraction': optics_values['extraction'],
        }
        self.data_set_saver.add_measurement('data', metadata)

        with open(self.machine_path / 'data.p', 'rb') as f:
            spectrum = pickle.load(f)

        times = np.arange(0, len(spectrum)) * 0.0000000004
        self.data_set_saver.save_points_batch('data', times, spectrum)
        time.sleep(5)


if __name__ == '__main__':
    TOF = Tof()

    for i in range(0, 10):  # number of spectra
        comment = 'This is a command line test IV'

        TOF.start_measurement(2.6e5)  # number of scans in each spectrum
        while True:
            time.sleep(3)
            print(TOF.read_acq_status())
            done = TOF.are_we_done_yet()
            if done:
                break
        time.sleep(1)
        with open(machine_path / 'data.p', 'rb') as f:
            spectrum = pickle.load(f)
        TOF.create_measurement_entry(comment)

        time.sleep(1 * 60)  # time between spectra
