import sys
import json
import time
import pickle
import socket
import pathlib
import logging
import traceback

import numpy as np

from icecream import ic

from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn
from PyExpLabSys.common.socket_clients import DateDataPullClient as DDPC
from PyExpLabSys.common.utilities import get_logger
import PyExpLabSys.drivers.agilent_34972A as multiplexer

HOSTNAME = socket.gethostname()
machine_path = pathlib.Path.home() / 'machines' / HOSTNAME
sys.path.append(str(machine_path))

import credentials  # pylint: disable=wrong-import-position, import-error

logging.basicConfig(
    filename="tof_run.log",
    format='%(asctime)s - %(levelname)s -- %(name)s:%(message)s',
    level=logging.INFO,
)
LOGGER = get_logger(
    'tof_run',
    file_max_bytes=104857,
    file_backup_count=2,
)


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
        print(hostname)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(0)
        self.sock.sendto(payload.encode(), (hostname, port))
        time.sleep(0.02)
        error = 0
        while True:
            try:
                recv = self.sock.recv(65535)
                print(recv)
                break
            except BlockingIOError as errmsg:
                print(errmsg)
                error += 1
                if error > 5:
                    ic('We have a communication issue')
                    time.sleep(0.5)
                else:
                    time.sleep(0.002)
        # print('recv: ', recv)
        raw_reply = recv.decode('ascii')
        return raw_reply

    def _command_gui(self, payload):
        """Send command to tof_run_gui.py"""
        socket_command = 'json_wn#' + json.dumps(payload)
        error = 0
        while error > -1:
            if error > 5:
                ic('We have a communication issue with tof_run_gui.py')
                time.sleep(0.5)
            try:
                self.sock.sendto(socket_command.encode(), ('127.0.0.1', 8500))
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

    def _read_emission_from_rasppi49(self):
        try:
            cli = DDPC('10.54.7.49', 'emission_tof', port=9000, timeout=0.5)
            values = cli.get_all_fields()
            return values['ionenergy'][1], values['emission'][1]
        except ValueError as err:
            LOGGER.error(traceback.format_exception_only(err))
            msg = 'Old values - check rasppi49'
            LOGGER.error(msg)
            print(msg)
            return 999999, 999999

    def _read_ion_optics_from_rasppi74(self):
        """Old optics values are:
        lens_a: -135.1 V
        lens_b: -60 V
        lens_c: -36 V
        lens_d: -39.5 V
        lens_e: -41.9 V
        focus: 12.8 V (emission focus voltage)
        extraction: -202 V
        """
        try:
            cli = DDPC('10.54.7.74', 'TOF_ion_optics', port=9000, timeout=0.5)
            optics_values = cli.get_all_fields()
            return {key: value[1] for key, value in optics_values.items()}
        except Exception as err:
            LOGGER.error(traceback.format_exception_only(err))
            msg = 'error from rasppi74'
            LOGGER.error(msg)
            print(msg)
            return {
                key: 0
                for key in [
                    'lens_a',
                    'lens_b',
                    'lens_c',
                    'lens_d',
                    'lens_e',
                    '',
                    'focus',
                    'extraction',
                ]
            }

    def _read_tof_voltages(self):
        try:
            mux = multiplexer.Agilent34972ADriver(hostname='tof-agilent-34972a')
            mux.set_scan_list(['106,107,108,109,110,111,112,115'])
            values = mux.read_single_scan()
            voltages = {
                'a2': values[6] * 10 / 0.9911,
                'deflection': 2200,  # hardcoded
                'focus': values[2] * 1000 / 0.9925,
                'liner': values[1] * 1000 / 0.9938,
                'mcp': values[0] * 1000 / 0.9943,
                'r1': values[4] * 1000 / 0.9931,
                'r2': values[5] * 1000 / 0.9875,
            }
            return voltages
        except Exception as err:
            LOGGER.error(traceback.format_exception_only(err))
            msg = 'Error from Agilent 34972A'
            LOGGER(msg)
            print(msg)
            errors = {
                key: 0
                for key in ['a2', 'deflection', 'focus', 'liner', 'mcp', 'r1', 'r2']
            }
            errors['deflection'] = 2200
            return errors

    def read_acq_status(self):
        try:
            cli = DDPC('127.0.0.1', 'tof-pull', port=9000, timeout=0.5)
            values = cli.get_all_fields()
            return values
        except Exception as err:
            LOGGER.error(traceback.format_exception_only(err))
            msg = 'tof_run_gui.py is not running correctly!'
            LOGGER.error(msg)
            print(msg)
            return {key: [0, 0] for key in ['starts', 'total_count', 'finished']}

    def start_measurement_in_sweeps(self, iterations):
        self.expected_iterations = iterations

        # TODO: Pulse voltage should be configurable!
        self.contact_external_pi('start_tof_measurement 800', 'rasppi74', 9696)
        # TODO! Remember to also send the stop command!
        time.sleep(2)

        payload = {
            'cmd': 'start_measurement',
            'sweeps': iterations,
            'iteration_time': 10,
        }
        self._command_gui(payload)
        return

    def start_measurement_in_minutes(self, minutes):

        # TODO: Pulse voltage should be configurable!
        self.contact_external_pi('start_tof_measurement 800', 'rasppi74', 9696)
        # TODO! Remember to also send the stop command!
        time.sleep(2)

        payload = {
            'cmd': 'start_measurement',
            'minutes': minutes,
            'iteration_time': 10,
        }
        self._command_gui(payload)
        return

    def are_we_done_yet(self):
        status = self.read_acq_status()
        done = status['finished'][1] == 1
        return done

    def abort_measurement(self):
        # 'cmd': 'quit',
        payload = {
            'cmd': 'abort_sweep',
        }
        self._command_gui(payload)
        return

    def create_measurement_entry(self, comment):
        tof_iterations = self.read_acq_status()['starts'][1]

        ion_energy, emission = self._read_emission_from_rasppi49()
        tof_voltages = self._read_tof_voltages()
        optics_values = self._read_ion_optics_from_rasppi74()
        tof_pulse_voltage = 800  # todo: Currently hard coded
        # deflection hard coded as well

        metadata = {
            # Endtime, should this have been starttime?
            'Time': CustomColumn(time.time(), "FROM_UNIXTIME(%s)"),
            'type': 11,
            'comment': comment,
            'tof_iterations': tof_iterations,
            'tof_pulse_voltage': tof_pulse_voltage,  # !
            'tof_liner_voltage': tof_voltages.get('liner', 0),
            'tof_lens_A': optics_values.get('lens_a', 0),
            'tof_lens_B': optics_values.get('lens_b', 0),
            'tof_lens_C': optics_values.get('lens_c', 0),
            'tof_lens_D': optics_values.get('lens_d', 0),
            'tof_lens_E': optics_values.get('lens_e', 0),
            'tof_ion_energy': ion_energy,
            'tof_R1_voltage': tof_voltages.get('r1', 0),
            'tof_R2_voltage': tof_voltages.get('r2', 0),
            'sem_voltage': tof_voltages.get('mcp', 0),
            'tof_deflection_voltage': tof_voltages['deflection'],  # !
            'tof_focus_voltage': tof_voltages.get('focus', 0),
            'tof_emission_current': emission,
            'emission_focus': optics_values.get('focus', 0),
            'emission_extraction': optics_values.get('extraction', 0),
        }
        self.data_set_saver.add_measurement('data', metadata)

        with open(self.machine_path / 'data.p', 'rb') as f:
            spectrum = pickle.load(f)

        times = np.arange(0, len(spectrum)) * 0.0000000004
        self.data_set_saver.save_points_batch('data', times, spectrum)
        time.sleep(5)


if __name__ == '__main__':
    LOGGER.info('Initializing TOF')
    TOF = Tof()
    t_start = time.time()
    i = 0

    ##########################################################
    # Enter settings                                         #
    ##########################################################
    duration = 1 / 60  # Acquire TOF spectra for this many hours

    # Comment for grouping spectra in database
    comment = '20250916_tof_software_test'

    # Sweep for x minutes / per spectrum
    sweep_time = 1

    ##########################################################
    # Start measurement loop                                 #
    ##########################################################
    nspectra = (duration * 60 - 25 / 60) / sweep_time  # Only for ETA
    while time.time() - t_start <= duration * 3600:
        i += 1
        LOGGER.info('Main measurement loop {}/~{}'.format(i, nspectra))
        # 1e6 scans/iterations/sweeps ~5 minutes and a few seconds

        TOF.start_measurement_in_minutes(sweep_time)  # X minutes per spectrum
        LOGGER.info('measurement started')
        while True:
            time.sleep(5)
            print(TOF.read_acq_status())
            done = TOF.are_we_done_yet()
            if done:
                break
        LOGGER.info('measurement finished')
        time.sleep(1)
        with open(machine_path / 'data.p', 'rb') as f:
            spectrum = pickle.load(f)
        LOGGER.info('data loaded - creating database entry...')
        TOF.create_measurement_entry(comment)
        LOGGER.info('measurement saved')
        time.sleep(10)  # time between spectra
