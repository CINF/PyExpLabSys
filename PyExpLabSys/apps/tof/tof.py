import json
import time
import pickle
import socket


class Tof():
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(0)
        self.expected_iterations = 0

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
        self.sock.sendto(socket_command.encode(), ('127.0.0.1', port))
        time.sleep(0.02)
        recv = self.sock.recv(65535)
        raw_reply = recv.decode('ascii')
        try:
            data = json.loads(raw_reply)
            value = data[1]
        except json.decoder.JSONDecodeError:
            value = raw_reply
        return value

    def read_acq_status(self):
        cmd = 'starts#json'
        starts = self._send_command(cmd, 9000)
        cmd = 'total_count#json'
        total_counts = self._send_command(cmd, 9000)
        reply = {'starts': starts, 'total_counts': total_counts}
        return reply

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
        cmd_list = ['lens_a', 'lens_b', 'lens_c', 'lens_d', 'lens_e', 'focus', 'extraction']
        optics_values = {}
        for cmd in cmd_list:
            raw_reply = self.contact_external_pi(cmd + '#json', '10.54.7.74', 9000)
            data = json.loads(raw_reply)
            optics_values[cmd] = float(data[1])
        return optics_values

    def _read_voltages_from_rasppi74(self):
        # todo: this does not need to be a separate function, but practical to test
        # We do not need to block while we wait the 9 seconds
        # time.sleep(9)
        # rasppi74.fys.clients.local (10.54.7.74):
        cmd = 'read_voltages\r'
        items_raw = self.contact_external_pi(cmd, '10.54.7.74', 9696)
        items = {}
        for item in items_raw.split(' '):
            if len(item) < 1:
                continue
            item_list = item.split(':')
            key = item_list[0]
            value = float(item_list[1])
            items[key] = value
        return items

    def start_measurement(self, iterations):
        self.expected_iterations = iterations

        # TODO: Pulse voltage should be configurable!
        self.contact_external_pi('start_tof_measurement 800', 'rasppi74', 9696)
        # TODO! Remember to also send the stop command!
        time.sleep(2)

        payload = {
            'cmd': 'start_measurement',
            'sweeps': iterations,
            'iteration_time': 5
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

        query = 'insert into {} set type=11, comment="{}", tof_iterations={}, '
        query += ' tof_pulse_voltage={}, tof_liner_voltage={},'
        query += ' tof_lens_A={}, tof_lens_B={}, tof_lens_C={}, tof_lens_D={}, tof_lens_e={},'
        query += ' ionenergy={}, R1_voltage={}, R2_voltage={},'
        query += ' sem_voltage={}, tof_focus_voltage,'
        query += ' tof_emission_current={}, emission_focus={}, emission_extraction={}'
        # tof_pulse_width  - apparantly always zero
        # tof_deflection_voltage ? From where
        # sample_temperature - seems not to be logged currently
        query = query.format(
            'tof',
            comment,
            tof_iterations,
            tof_pulse_voltage,
            tof_voltages['liner'],
            optics_values['lens_a'],
            optics_values['lens_b'],
            optics_values['lens_c'],
            optics_values['lens_d'],
            optics_values['lens_e'],
            ion_energy,
            tof_voltages['r1'],
            tof_voltages['r2'],
            tof_voltages['mcp'],
            tof_voltages['focus'],
            emission,
            optics_values['focus'],
            optics_values['extraction'],
        )
        print(query)


if __name__ == '__main__':
    TOF = Tof()
    comment = 'This is a command line test'

    TOF.start_measurement(95000)
    for i in range(0, 25):
        time.sleep(2)
        print(TOF.read_acq_status())
        done = TOF.are_we_done_yet()
        if done:
            break

    with open('data.p', 'rb') as f:
        spectrum = pickle.load(f)

    TOF.create_measurement_entry(comment)
