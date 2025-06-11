import time
import numpy as np
from ps_measurement_base import ProbeStationMeasurementBase


class ProbeStation2PointDoubleSteppedVSource(ProbeStationMeasurementBase):
    def __init__(self):
        # super().__init__(self=self)
        super().__init__()
        self.aborted = False
        time.sleep(0.2)

    def abort_measurement(self):
        print('ABORT')
        self.aborted = True
        self.reset_current_measurement('aborting', error='Aborted', keep_measuring=True)

    def _setup_data_log(self, comment, source, gate):
        labels = {'v_backgate': 'Gate voltage'}
        self._add_metadata(
            labels,
            303,
            comment,
            steps=gate['steps'],
            repeats=gate['repeats'],
            nplc=gate['nplc'],
        )
        labels = {'i_backgate': 'Gate current'}
        self._add_metadata(labels, 303, comment, nplc=gate['nplc'], limit=gate['limit'])

        labels = {'v_source': 'Vsource'}
        self._add_metadata(
            labels,
            303,
            comment,
            steps=source['steps'],
            repeats=source['repeats'],
            nplc=source['nplc'],
        )
        labels = {'current': 'Current'}
        self._add_metadata(
            labels, 303, comment, nplc=source['nplc'], limit=source['limit']
        )
        self.reset_current_measurement('2PointDoubleSteppedVSource')

    def dc_2_point_measurement_v_source(
        self, comment, inner: str, source: dict, gate: dict, params: dict, **kwargs
    ):
        """
        Perform a 2-point DC vi-measurement.
        """
        # TODO! Store information about readback and auto-zero in metadata!
        self._setup_data_log(comment=comment, source=source, gate=gate)
        self._configure_instruments(source=source, gate=gate, params=params)

        # Calculate the sweeps
        gate_steps = self._calculate_steps(
            low=gate['v_low'],
            high=gate['v_high'],
            repeats=gate['repeats'],
            steps=gate['steps'],
        )
        source_steps = self._calculate_steps(
            low=source['v_low'],
            high=source['v_high'],
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
                # This is a 2-wire measurement, no need for DMM
                self.read(read_dmm=False)

        time.sleep(2)

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
        self.dc_2_point_measurement_v_source(
            comment='test() - double stepped',
            # inner='source',  # outer will be gate
            inner='gate',  # ourter will be source
            params={'autozero': False, 'readback': False, 'source_measure_delay': 1e-3},
            source={
                'v_low': -0.2,
                'v_high': 1.0,
                'repeats': 0,
                'steps': 5,
                'limit': 1e-2,
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
    ps = ProbeStation2PointDoubleSteppedVSource()
    ps.test()
