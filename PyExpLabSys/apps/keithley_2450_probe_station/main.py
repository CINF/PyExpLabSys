import time
import json
import threading

from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import DateDataPullSocket

from ps_measurement_base import ProbeStationMeasurementBase

from ps_double_stepped_4point_dc_i_source import ProbeStation4PointDoubleSteppedISource
from ps_double_stepped_2point_dc_v_source import ProbeStation2PointDoubleSteppedVSource


class ProbeStationController(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.quit = False

        self.measurement = ProbeStationMeasurementBase()

        self.pushsocket = DataPushSocket('probe_station', action='enqueue', port=8510)
        self.pushsocket.start()

        self.pullsocket = DateDataPullSocket(
            'probestation',
            ['status', 'simulation', 'next_sim', 'v_source', 'v_tot'],
            timeouts=[999999, 999999, 999999, 3, 3],
            port=9002,
        )
        self.pullsocket.start()

    def start_2point_double_stepped_v_source(self, **kwargs):
        # TODO: Check that measurement is not already running
        self.measurement.stop()
        del self.measurement
        self.measurement = ProbeStation2PointDoubleSteppedVSource()
        t = threading.Thread(
            target=self.measurement.dc_2_point_measurement_v_source, kwargs=kwargs
        )
        t.start()
        return True

    def start_4point_double_stepped_i_source(self, **kwargs):
        # TODO: Check that measurement is not already running
        self.measurement.stop()
        del self.measurement
        self.measurement = ProbeStation4PointDoubleSteppedISource()
        t = threading.Thread(
            target=self.measurement.dc_4_point_measurement_i_source, kwargs=kwargs
        )
        t.start()
        return True

    def _handle_element(self, element):
        cmd = element.get('cmd')
        if cmd == 'start_measurement':
            # This only works on first run - change into check for
            if self.measurement.current_measurement['type'] is not None:
                print('Measurement running, cannot start new')
                return
            if element.get('measurement') == '2point_double_stepped_v_source':
                self.start_2point_double_stepped_v_source(**element)
            if element.get('measurement') == '4point_double_stepped_i_source':
                self.start_4point_double_stepped_i_source(**element)

        elif cmd == 'abort':
            if self.measurement.current_measurement['type'] is not None:
                self.measurement.abort_measurement()

        elif cmd == 'simulate':
            """Create an approximate graph of the submitted ramp"""
            simulation = self.measurement.step_simulator(**element)
            self.sim_dump = json.dumps(simulation)
            self.pullsocket.set_point_now('simulation', 'START')
            self.pullsocket.set_point_now('next_sim', '')
            print('Updated simulation')
        elif cmd == 'next_sim':
            print('next_sim')
            next_sim = self.sim_dump[0:25000]
            self.sim_dump = self.sim_dump[25000:]
            self.pullsocket.set_point_now('next_sim', next_sim)

        # TODO!!!!
        elif cmd == 'set_manual_gate':
            if self.measurement.current_measurement['type'] is None:
                voltage = element.get('gate_voltage', 0)
                current_limit = element.get('gate_current_limit', 1e-8)
                self.measurement.back_gate.set_source_function('v')
                self.measurement.back_gate.set_current_limit(current_limit)
                self.measurement.back_gate.set_voltage(voltage)
                self.measurement.back_gate.output_state(True)

        # elif cmd == 'toggle_source':
        # elif cmd == 'toggle_gate':
        #     if self.measurement.current_measurement['type'] is None:
        #         state = self.measurement.current_source.output_state()
        #         self.measurement.current_source.output_state(not state)

        else:
            print('Unknown command')

    def run(self):
        while not self.quit:
            time.sleep(0.001)
            # print('Running')
            # Check if measurement is running and set self.measurement to None of not
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                qsize = self.pushsocket.queue.qsize()
                self._handle_element(element)

            # Do not feed socket with old data, update v_xx only if a measurement
            # is running
            if self.measurement.current_measurement['type'] is not None:
                if len(self.measurement.current_measurement['v_source']) > 2:
                    self.pullsocket.set_point_now(
                        'v_source', self.measurement.current_measurement['v_source'][-1]
                    )
            status = {
                'type': self.measurement.current_measurement['type'],
                'start_time': self.measurement.current_measurement['start_time'],
            }
            self.pullsocket.set_point_now('status', status)

            if self.measurement.current_measurement['type'] is None:
                # gate_v = self.measurement.read_gate(store_data=False)
                # print(gate_v)
                # self.measurement.dmm.trigger_source(external=False)
                # self.measurement.dmm.measurement_range(0)
                # voltage = self.measurement.dmm.next_reading()
                # voltage = self.measurement.dmm.read()
                if self.measurement.dmm_reader is not None:
                    voltage = self.measurement.dmm_reader.value
                    self.pullsocket.set_point_now('v_tot', voltage)
                # TODO: Otherwise use the 2450


def main():
    pc = ProbeStationController()
    # cm.dc_4_point_measurement(1e-6, 1e-4)
    pc.start()


if __name__ == '__main__':
    main()
