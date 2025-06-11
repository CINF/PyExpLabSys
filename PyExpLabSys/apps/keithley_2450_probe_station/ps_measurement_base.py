import json
import time
import socket
import pathlib
import tomllib

import numpy as np

from PyExpLabSys.drivers.keithley_2450 import Keithley2450
from ps_dmm_reader import ProbeStationDMMReader

# Todo: Check why CustomColumn is needed???
from PyExpLabSys.common.database_saver import DataSetSaver, CustomColumn

# import credentials

CURRENT_MEASUREMENT_PROTOTYPE = {
    'type': None,  # DC-sweep, AC-sweep
    'error': None,
    'start_time': 0,
    'current_time': 0,
    'current': [],
    'v_total': [],
    'v_source': [],
    'v_backgate': [],  # Back gate voltage
    'i_backgate': [],  # Bakc gate leak-current
}


# Todo: This is now in practice a TSP-link base
# If we want to also implement fully software timed measurements (to be used
# without TSP-link), this should be separated into common base and a TSP-link base.
class ProbeStationMeasurementBase(object):
    def __init__(self):
        self.current_measurement = CURRENT_MEASUREMENT_PROTOTYPE.copy()

        host = socket.gethostname()
        home = pathlib.Path.home() / 'machines' / host
        with open(home / 'config.toml', 'rb') as f:
            self.config = tomllib.load(f)
        with open(home / 'credentials.toml', 'rb') as f:
            self.credentials = tomllib.load(f)

        dmm_visa = self.config['dmm_visa_string']
        if not dmm_visa:
            print('No DMM configured')
            self.dmm_reader = None
        else:
            self.dmm_reader = ProbeStationDMMReader(dmm_visa)
            self.dmm_reader.start()

        tsp_link_ip = self.config['tsp_link_ip']
        self.tsp_link = Keithley2450(interface='lan', hostname=tsp_link_ip)
        self.tsp_link.instr.timeout = 10000

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(1)
        self.sock.settimeout(1.0)

        self.chamber_name = self.config['chamber_name']
        self.data_set_saver = DataSetSaver(
            "measurements_" + self.chamber_name,
            "xy_values_" + self.chamber_name,
            self.credentials['user'],
            self.credentials['passwd'],
        )
        self.data_set_saver.start()

    def stop(self):
        if self.dmm_reader is not None:
            self.dmm_reader.running = False
        time.sleep(0.5)

    def _read_socket(self, cmd):
        try:
            self.sock.sendto(cmd.encode(), ('127.0.0.1', 9000))
            recv = self.sock.recv(65535)
            data = json.loads(recv)
            value = data[1]
        except socket.timeout:
            print('Lost access to socket')
            value = None
        return value

    def prepare_tsp_triggers(self):
        """
        This defines the TSP-code needed for 2-point DC and 4-point DC measurements
        Node 1 is the gate and is acting as main unit. Node 2 is source-drain and
        will recieve all comands via TSP-link from node 1

        Todo:
        If we want to implent more fancy stuff, eg. delta mode or differential
        conductance measurements, some of the trigger model code needs
        to be refactored
        """
        # TODO: Seems there is a bug in second notify block, this should
        # be connected to digital out 1, but is unconnected until manually
        # set from front panel...
        preparescript = pathlib.Path('prepare_tsp_triggers.lua').read_text()
        self.tsp_link.load_script('preparescript', preparescript)
        self.tsp_link.execute_script('preparescript')
        return

    def reset_current_measurement(
        self, measurement_type, error=False, keep_measuring=False
    ):
        """
        Reset current data if a new measurement is about to start.
        If measurement_type is None, this indicates that the measurement
        stops, in this case keep the data for now.
        """
        if measurement_type is None:
            self.current_measurement['type'] = None
            self.current_measurement['error'] = error
        else:
            for key, value in self.current_measurement.items():
                if isinstance(value, list):
                    self.current_measurement[key].clear()
            if not keep_measuring:
                self.current_measurement.update(
                    {
                        'type': measurement_type,
                        'start_time': time.time(),
                        'current_time': time.time(),
                    }
                )
            else:
                self.current_measurement.update({'type': measurement_type})

        return True

    def add_to_current_measurement(self, data_point: dict):
        """
        Here we store the data, both permenantly in the database
        and temporarely in the local dict self.current_measurement
        """
        now = time.time() - self.current_measurement['start_time']
        for key in self.current_measurement.keys():
            if key in data_point:
                value = data_point[key]
                self.current_measurement[key].append((now, value))
                self.data_set_saver.save_point(key, (now, value))
        self.current_measurement['current_time'] = time.time()

    def _add_metadata(
        self,
        labels,
        meas_type,
        comment,
        nplc=None,
        limit=None,
        steps=None,
        repeats=None,
    ):
        metadata = {
            'Time': CustomColumn(time.time(), "FROM_UNIXTIME(%s)"),
            'label': None,
            'type': meas_type,
            'comment': comment,
            'nplc': nplc,
            'limit': limit,
            'steps': steps,
            'repeats': repeats,
        }
        for key, value in labels.items():
            metadata.update({'label': value})
            self.data_set_saver.add_measurement(key, metadata)
        return True

    def abort_measurement(self):
        print('ABORT')
        self.reset_current_measurement(None, error='Aborted')

    def _check_I_source_status(self):
        """
        Check that source is not in compliance. If it is, the system
        shoudl be stopped (or not depending on configuration).
        """
        # Here we should check variables as set by read() and and stop the
        # measurement if appropriate
        # :OUTPut[1]:INTerlock:TRIPped?
        source_ok = True
        return source_ok

    def _ramp_gate(self, v_from, v_to, rate=0.5, force_even_if_abort=False):
        # Rate is the allowed gate-sweep rate in V/s
        # todo: strongly consider to move this up to dc_base
        sign = np.sign(v_to - v_from)
        if sign == 0:
            self.tsp_link.set_output_level(0, node=1)
            return
        step_size = 0.025

        if abs(v_to - v_from) < 3 * step_size:
            # This is not really a ramp, this is a continous sweep that we can
            # accept to performin one go:
            msg = 'Small step, set gate directly: {:.1f}mV'
            print(msg.format(1000 * abs(v_to - v_from)))
            # self.back_gate.set_voltage(v_to)
            self.tsp_link.set_output_level(v_to, node=1)
            return

        print('Ramp gate: ', v_from, v_to, step_size, sign)
        ramp_list = list(np.arange(v_from, v_to, step_size * sign)) + [v_to]
        for gate_ramp_v in ramp_list:
            if (self.current_measurement['type'] == 'aborting') and (
                not force_even_if_abort
            ):
                print('Measurement aborted - stop gate ramp')
                break
            print('Ramping gate to {}'.format(gate_ramp_v))
            self.tsp_link.set_output_level(gate_ramp_v, node=1)
            self.read()
            time.sleep(step_size / rate)

    # This code is also used in the Linkham code
    def _calculate_steps(self, low, high, steps, repeats=1, **kwargs):
        """
        Calculate a set steps from low to high and back.
        If repeats is 0, the ramps starts directly from low, otherwise
        all values are swept from 0.
        All ramps will always and at 0.

        **kwargs used only to eat extra arguments from network syntax
        Todo: Consider to move to a common library since so many setups use it
        """
        delta = high - low
        if steps < 2:
            return [low]
        step_size = delta / (steps - 1)

        if repeats == 0:
            start = low
        else:
            start = 0

        # From 0 to high
        up = list(np.arange(start, high, step_size))
        # high -> 0
        down = list(np.arange(high, start, -1 * step_size))

        # N * (high -> low -> high)
        zigzag = (
            list(np.arange(high, low, -1 * step_size))
            + list(np.arange(low, high, step_size))
        ) * repeats
        step_list = up + zigzag + down + [0]
        return step_list

    def step_simulator(
        self, inner: str, source: dict, gate: dict, params: dict, **kwarg
    ):
        gate_steps = self._calculate_steps(
            low=gate['v_low'],
            high=gate['v_high'],
            repeats=gate['repeats'],
            steps=gate['steps'],
        )
        if 'v_low' in source:
            low = 'v_low'
            high = 'v_high'
        else:
            low = 'i_low'
            high = 'i_high'
        source_steps = self._calculate_steps(
            low=source[low],
            high=source[high],
            repeats=source['repeats'],
            steps=source['steps'],
        )
        assert inner.lower() in ('source', 'gate')
        if inner.lower() == 'source':
            inner_steps = source_steps
            outer_steps = gate_steps
            nplc = source['nplc']
        else:
            inner_steps = gate_steps
            outer_steps = source_steps
            nplc = gate['nplc']

        if params['readback']:
            # If readback is enabled, measurements will take twice as long
            nplc = nplc * 2

        # Notice, gate-protection ramping is currently not simulated, but the
        # generation of the steps is done iteratively, so it should not be
        # difficult to do at a later stage
        dt = 0
        simulation = {
            'time': [],
            'inner': [],
            'outer': [],
        }
        for outer_step in outer_steps:
            for inner_step in inner_steps:
                simulation['time'].append(dt)
                simulation['outer'].append(outer_step)
                simulation['inner'].append(inner_step)
                # Notice! Autozero is not simulated
                dt = dt + nplc + params['source_measure_delay']
        return simulation

    def _configure_instruments(self, source: dict, gate: dict, params: dict):
        """
        Configures the Keithley 2450's using the TSP link
        Gate always have v_low and v_high key. Source has either v_low and v_high
        or i_low and i_high depending on of the measurement is constant voltage
        or constant current.
        :param source: The configuration of the source
        :param source: The configuration of the gate
        :param source: General parameters: read_back and auto-zero
        """
        print('Configure tsp-instruments')
        self.prepare_tsp_triggers()

        gate_range = max(abs(gate['v_low']), abs(gate['v_high']))
        if 'v_low' in source:
            source_range = max(abs(source['v_high']), abs(source['v_low']))
            source_function = 'v'
            sense_function = 'i'
        else:
            source_range = max(abs(source['i_high']), abs(source['i_low']))
            source_function = 'i'
            sense_function = 'v'

        self.tsp_link.clear_output_queue()
        use_rear = self.config['use_rear_terminals']
        self.tsp_link.use_rear_terminals(node=1, use_rear=use_rear)
        self.tsp_link.use_rear_terminals(node=2, use_rear=use_rear)

        self.tsp_link.set_source_function(function='v', source_range=gate_range, node=1)
        # Temporarily set sense to auto to avoid temporary range conflicts
        self.tsp_link.set_sense_function(function='i', sense_range=0, node=1)

        self.tsp_link.set_limit(gate['limit'], node=1)
        self.tsp_link.set_sense_function(
            function='i', sense_range=gate['limit'], node=1
        )
        # Always use 2-point measurement for the gate
        self.tsp_link.remote_sense(False, node=1)
        self.tsp_link.set_integration_time(nplc=gate['nplc'], node=1)

        self.tsp_link.set_source_function(
            source_function, source_range=source_range, node=2
        )
        # Temporarily set sense to auto to avoid temporary range conflicts
        self.tsp_link.set_sense_function(sense_function, sense_range=0, node=2)
        self.tsp_link.set_limit(source['limit'], node=2)
        self.tsp_link.set_sense_function(
            sense_function, sense_range=source['limit'], node=2
        )
        self.tsp_link.set_integration_time(nplc=source['nplc'], node=2)

        for node in (1, 2):
            time.sleep(0.25)
            self.tsp_link.clear_buffer(node=node)
            self.tsp_link.set_readback(action=params['readback'], node=node)
            self.tsp_link.set_output_level(0, node=node)
            self.tsp_link.output_state(True, node=node)
            self.tsp_link.set_auto_zero(params['autozero'], node=node)
            self.tsp_link.auto_zero_now(node=node)
            self.tsp_link.clear_buffer(node=node)

        # If remote sense is activated with output off, a warning is issued
        if 'v_low' in source:
            self.tsp_link.remote_sense(False, node=2)
        else:
            self.tsp_link.remote_sense(True, node=2)

        # Note: The model of running the trigger model with a single measurement
        # and repeatedly trigger seems to have an overhead of approximately ~0.3NPLC
        # compared to a fully configured trigger sweep
        execute_iteration = """
        node[2].trigger.model.initiate()
        trigger.model.initiate()
        waitcomplete()
        n = node[1].defbuffer1.endindex
        m = node[2].defbuffer1.endindex
        printbuffer(n, n, node[1].defbuffer1, node[1].defbuffer1.units, node[1].defbuffer1.sourcevalues)
        printbuffer(m, m, node[2].defbuffer1, node[2].defbuffer1.units, node[2].defbuffer1.sourcevalues)
        print("end " .. n .. " " .. m)
        """
        # print(execute_iteration)
        execute_iteration = pathlib.Path('execute_iteration.lua').read_text()
        # print()
        # print(execute_iteration2)
        # exit()
        self.tsp_link.load_script('execute_iteration', execute_iteration)
        print('Configure done')

    def read(self, read_dmm=False):
        self.tsp_link.execute_script('execute_iteration')
        # This script always output exactly three lines
        gate = self.tsp_link.instr.read().strip().split(',')
        source = self.tsp_link.instr.read().strip().split(',')

        if 'Amp' in source[1]:
            current = float(source[0])
            v_source = float(source[2])
        else:
            current = float(source[2])
            v_source = float(source[0])

        # Control should always be 'end n m' with n and m both being the
        # current iteration number
        # Todo: Assert this...
        control = self.tsp_link.instr.read().strip()

        # Todo: Check status if device is in compliance
        data = {
            'i_backgate': float(gate[0]),
            'v_backgate': float(gate[2]),
            'v_source': v_source,
            'current': current,
        }

        # TODO! This needs to be implemented and testet. The trigger is already
        # running all we need is to make sure we can read fast enough from usb
        if self.dmm_reader and read_dmm:
            v_total = self.dmm_reader.value
            # raw = self.dmm.scpi_comm(':FETCH?')
            # print(raw)
            # v_total = self.dmm.read_dc_voltage()
            # v_total = float(raw)
            data['v_total'] = v_total

        self.add_to_current_measurement(data)
        return data

    def dummy_background_measurement(self):
        # This should be a simple measurement that runs
        # when nothing else is running and allowing to
        # show status data such as current and DMM voltage
        # in the frontend
        pass


if __name__ == '__main__':
    pass
