import time
import numpy as np

# from ps_dc_base import ProbeStationDCBase
from ps_measurement_base import ProbeStationMeasurementBase


class ProbeStation4PointDoubleSteppedISource(ProbeStationMeasurementBase):
    def __init__(self):
        # super().__init__(self=self)
        super().__init__()
        self.aborted = False
        time.sleep(0.2)

    def abort_measurement(self):
        print('ABORT')
        self.tsp_link.set_output_level(0)
        self.aborted = True
        self.reset_current_measurement('aborting', error='Aborted', keep_measuring=True)

    def _setup_data_log(self, comment, source, gate):
        labels = {'v_total': 'Vtotal'}
        self._add_metadata(labels, 302, comment)

        labels = {'v_backgate': 'Gate voltage'}
        self._add_metadata(labels, 302, comment, nplc=gate['nplc'])
        labels = {'i_backgate': 'Gate current'}
        self._add_metadata(labels, 302, comment, nplc=gate['nplc'], limit=gate['limit'])

        labels = {'v_source': 'Vsource'}
        self._add_metadata(labels, 302, comment, nplc=source['nplc'])
        labels = {'current': 'Current'}
        self._add_metadata(
            labels, 302, comment, nplc=source['nplc'], limit=source['limit']
        )
        self.reset_current_measurement('4PointDoubleStepped')

    def dc_4_point_measurement_i_source(
        self, comment, inner: str, source: dict, gate: dict, params: dict, **kwargs
    ):
        """
        Perform a 4-point DC vi-measurement.
        :param start: The lowest voltage in the sweep
        :param stop: The highest voltage in the sweep
        :param steps: Number of steps in sweep
        :param nplc: Integration time of  measurements
        :params gate_v: Optional gate voltage at which the sweep is performed
        :v_limit: Maximal allowed voltage, default is 1.0
        """
        self._setup_data_log(comment=comment, source=source, gate=gate)
        self._configure_instruments(source=source, gate=gate, params=params)
        # self.configure_dmm(source['limit'], source['nplc'])

        # Calculate the sweeps
        gate_steps = self._calculate_steps(
            low=gate['v_low'],
            high=gate['v_high'],
            repeats=gate['repeats'],
            steps=gate['steps'],
        )
        source_steps = self._calculate_steps(
            low=source['i_low'],
            high=source['i_high'],
            repeats=source['repeats'],
            steps=source['steps'],
        )

        assert inner.lower() in ('source', 'gate')
        if inner.lower() == 'source':
            inner_steps = source_steps
            outer_steps = gate_steps
            inner_node = 2  # Source
            outer_node = 1  # Gate
        else:
            inner_steps = gate_steps
            outer_steps = source_steps
            inner_node = 1  # Gate
            outer_node = 2  # Source

        latest_gate = 0
        for outer_v in outer_steps:
            if self.current_measurement['type'] == 'aborting':
                continue
            print('Set outer to: {}'.format(outer_v))
            self.tsp_link.auto_zero_now(node=1)
            self.tsp_link.auto_zero_now(node=2)

            if inner.lower() == 'gate':
                self.tsp_link.set_output_level(outer_v, node=outer_node)
            else:
                self._ramp_gate(v_from=latest_gate, v_to=outer_v)
                latest_gate = outer_v

            for inner_v in inner_steps:
                if self.current_measurement['type'] == 'aborting':
                    # Measurement has been aborted, skip through the
                    # rest of the steps
                    continue

                print('Set inner to {}'.format(inner_v))
                if inner.lower() == 'source':
                    self.tsp_link.set_output_level(inner_v, node=inner_node)
                else:
                    self._ramp_gate(v_from=latest_gate, v_to=inner_v)
                    latest_gate = inner_v
                time.sleep(params['source_measure_delay'])

                if not self._check_I_source_status():
                    # TODO!!! This always returns True!!!!
                    return
                # Todo: This is a 4 (3....) point measurement - read DMM!
                self.read(read_dmm=True)

        time.sleep(1)

        data = self.read()
        v_from = data['v_backgate']
        if not self.aborted:
            self._ramp_gate(v_from=v_from, v_to=0)
            self.reset_current_measurement(None)
        else:
            print('Ramp gate back to zero')
            self._ramp_gate(v_from=v_from, v_to=0, force_even_if_abort=True)
            self.reset_current_measurement(None, error='Aborted')

        # Indicate that the measurement is completed
        self.aborted = False
        self.tsp_link.output_state(False, node=1)
        self.tsp_link.output_state(False, node=2)
        self.reset_current_measurement(None)

    def test(self):
        # self.instrument_id()
        self.dc_4_point_measurement_i_source(
            comment='test() - double stepped',
            # inner='source',  # outer will be gate
            inner='gate',  # ourter will be source
            params={'autozero': False, 'readback': False, 'source_measure_delay': 1e-3},
            source={
                'i_low': -5e-4,
                'i_high': 2e-3,
                'repeats': 0,
                'steps': 5,
                'limit': 2,
                'nplc': 1,
                'step_type': 'linear',
            },
            gate={
                'v_low': -1.0,
                'v_high': 5.0,
                'steps': 101,
                'repeats': 1,
                'nplc': 1,
                'limit': 1e-5,
                'step_type': 'linear',
            },
        )


if __name__ == '__main__':
    ps = ProbeStation4PointDoubleSteppedISource()
    ps.test()
