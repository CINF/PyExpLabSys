from PyQt5 import QtWidgets, QtCore, uic
from PyQt5.QtWidgets import QMessageBox

# from PyQt5.QtWidgets import QTableWidgetItem

QtCore.QCoreApplication.setSetuidAllowed(True)

# from pyqtgraph import PlotWidget
import pyqtgraph as pg

import sys
import time
import json
import pickle
import socket


IP = 10.54.5.244


class InvalidFieldError(Exception):
    pass


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.write_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.write_socket.setblocking(0)

        # Used for continous communication with cryostat
        self.read_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.read_socket.setblocking(0)
        self.read_socket_in_use = False

        self.latest_measurement_type = None
        self.t_start = time.time()
        uic.loadUi('probestation.ui', self)
        # I am not sure how to set this default in QTDesigner...
        self.nplc.setCurrentText('1')

        self.set_manual_gate_button.clicked.connect(self._set_manual_gate)
        self.toggle_k6221_button.clicked.connect(self._toggle_k6221)

        # Connect to buttons
        self.DC2pGateSweep_start_button.clicked.connect(self._start_2p_dc_gate_sweep)
        # self.DC2pGateSweep_simulate_button.clicked.connect(
        #     self._simulate_2p_dc_gate_sweep)
        self.DC2pGateSweep_simulate_button.clicked.connect(
            self._simulate_2p_dc_gate_sweep
        )
        # self.DC2pGateSweep_start_button.clicked.connect(
        #    self.self._start_4p_dc_gate_sweep)

        self.abort_measurement_button.clicked.connect(self._abort_measurement)

        self.gate_plot.setBackground('w')
        self.gate_plot.setLabel(axis='left', text='Voltage / V')
        self.gate_plot.setLabel(axis='bottom', text='Time')

        self.source_plot.setBackground('w')
        self.source_plot.setLabel(axis='left', text='Voltage / V')
        self.source_plot.setLabel(axis='bottom', text='Time')

        self.simulation_plot.setBackground('w')
        self.simulation_plot.setLabel(axis='left', text='Source / V')
        self.simulation_plot.showAxis('right')
        self.simulation_plot.setLabel(axis='right', text='Gate / V')
        self.simulation_plot.setLabel(axis='bottom', text='Time')

        self.status_plot.setBackground('w')
        # This axis might be updated by individual measurements
        self.status_plot.setLabel(axis='left', text='Voltage')
        self.status_plot.setLabel(axis='bottom', text='Time')

        self.source_voltage_x = []
        self.source_voltage_y = []
        self.gate_voltage_x = []
        self.gate_voltage_y = []
        # self.source_current__x = []
        # self.source_current_y = []
        # self.gate_current__x = []
        # self.gate_current_y = []

        self.measurement_plot_x = []
        self.measurement_plot_y = []

        # Set up plots - consider to refactor out of this function
        pen = pg.mkPen(color=(255, 0, 0))
        pen2 = pg.mkPen(color=(0, 0, 255))
        self.gate_voltage_line = self.gate_plot.plot(
            self.gate_voltage_x, self.gate_voltage_y, pen=pen
        )
        self.source_voltage_line = self.source_plot.plot(
            self.source_voltage_x, self.source_voltage_y, pen=pen2
        )
        self.measurement_line = self.status_plot.plot(
            self.measurement_plot_x, self.measurement_plot_y, pen=pen
        )

        # Simulation plot
        self.right_vb = pg.ViewBox()
        self.simulation_plot.scene().addItem(self.right_vb)
        self.simulation_plot.getAxis('right').linkToView(self.right_vb)
        self.right_vb.setXLink(self.simulation_plot.plotItem)

        self.simulation_inner_line = self.simulation_plot.plot(
            [1, 2, 3, 4, 5], [105, 104, 103, 102, 101], pen=pen, name='Inner'
        )
        # self.simulation_outer_line = self.simulation_plot.plot(
        #    [1, 2, 3, 4, 5], [1, 2, 3, 4, 5], pen=pen2
        # )
        self.simulation_outer_line = pg.PlotCurveItem(
            [1, 2, 3, 4, 5], [1, 2, 3, 4, 5], pen=pen2, name='Outer'
        )
        self.right_vb.addItem(self.simulation_outer_line)
        self.simulation_plot.autoRange()
        # Connect the resizeEvent signal to the updateViews function
        self.simulation_plot.getViewBox().sigResized.connect(self.updateViews)
        # Show the right axis
        self.simulation_plot.getAxis('right').show()

        self.simulation_plot.addLegend()

        self.timer = QtCore.QTimer()
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_plot_data)
        self.timer.start()

    def updateViews(self):
        """
        Updates the views of the plot to keep the right y-axis in sync.
        """
        # Set the geometry of the right ViewBox to match the main ViewBox
        self.right_vb.setGeometry(self.simulation_plot.getViewBox().sceneBoundingRect())
        # Update the linked axes
        self.right_vb.linkedViewChanged(
            self.simulation_plot.getViewBox(), self.right_vb.XAxis
        )

    def alert(self, msg):
        box = QMessageBox()
        box.setIcon(QMessageBox.Critical)
        box.setText(msg)
        box.setWindowTitle(msg)
        box.exec_()

    def _read_field(self, x, y):
        """
        Read a specific field in the ramp table.
        If the field is empty None is returned.
        If the field cannot be read as float, an exception is raised
        """
        item = self.ramp_table.item(x, y)
        if item is None:
            return None
        if len(item.text()) == 0:
            return None
        try:
            value = float(item.text())
        except ValueError:
            self.alert('Value error in ramp')
            # msg = QMessageBox()
            # msg.setIcon(QMessageBox.Critical)
            # msg.setText('Value error in ramp')
            # msg.setWindowTitle("Error")
            # msg.exec_()
            value = None
            raise InvalidFieldError
        return value

    def _parse_ramp(self):
        ramp = []
        i = 0
        while i > -1:
            try:
                dt = self._read_field(i, 0)
                temp = self._read_field(i, 1)
                b_field = self._read_field(i, 2)
            except InvalidFieldError:
                return
            if None in (dt, temp, b_field):
                break

            ramp.append({'dt': dt, 'temp': temp, 'b_field': b_field})
            i = i + 1
        return ramp

    def _write_socket(self, cmd, port=8500):
        socket_cmd = 'json_wn#' + json.dumps(cmd)
        self.read_socket.sendto(socket_cmd.encode(), (IP, port))
        time.sleep(0.1)
        recv = self.read_socket.recv(65535).decode('ascii')
        print(recv)
        assert 'ACK' in recv

    def _update_via_socket(self, command, setpoint):
        command = {
            # 'cmd': 'vti_temperature_setpoint',
            'cmd': command,
            'setpoint': setpoint,
            'slope': 5,  # K/min, so far hardcodet and not in use
        }
        self._write_socket(command)
        # todo: Check reply that command is acknowledged

    def _toggle_k6221(self):
        command = {'cmd': 'toggle_6221'}
        self._write_socket(command, 8510)

    def _set_manual_gate(self):
        command = {
            'cmd': 'set_manual_gate',
            'gate_voltage': self.manual_gate_voltage.value(),
            'gate_current_limit': self.manual_gate_current_limit.value() * 1e-6,
        }
        print(command)
        self._write_socket(command, 8510)

    def _read_simulation(self, command):
        command['cmd'] = 'simulate'
        # Ask backend to update simulation with current parameters:
        self._write_socket(command, 8510)
        time.sleep(0.1)

        simulation_raw = b''
        while True:
            # Ask backend to update the pullsocket with next part of simulation
            command_next_sim = {'cmd': 'next_sim'}
            self._write_socket(command_next_sim, 8510)
            time.sleep(0.005)
            # Probe the pull socket
            socket_command = 'next_sim#raw'
            self.read_socket.sendto(socket_command.encode(), (IP, 9002))
            time.sleep(0.005)
            recv = self.read_socket.recv(65535)
            content = recv[recv.find(b',') + 1 :]
            simulation_raw += content
            if len(content) == 0:
                break
        simulation = json.loads(simulation_raw)
        return simulation

    def _abort_measurement(self):
        command = {'cmd': 'abort'}
        self._write_socket(command, 8510)

    def _start_2p_dc_gate_sweep(self, no_execution=False):
        comment = self.measurement_comment.text()
        if len(comment) < 5:
            self.alert('Comment too short')
            return False
        if self.DC2pGateSweep_source_inner_loop_label_box.currentText() == 'Gate':
            inner = 'gate'
        else:
            inner = 'source'
        command = {
            'cmd': 'start_measurement',
            'measurement': '2point_double_stepped_v_source',
            'comment': comment,
            'inner': inner,
            'gate': {
                'v_low': self.DC2pGateSweep_gate_low.value(),
                'v_high': self.DC2pGateSweep_gate_high.value(),
                'steps': int(self.DC2pGateSweep_gate_steps.value()),
                'repeats': int(self.DC2pGateSweep_gate_repeats.value()),
                'nplc': float(self.nplc.currentText()),
                'limit': self.gate_max_current.value() * 1e-6,
            },
            'source': {
                'v_low': self.DC2pGateSweep_source_low.value(),
                'v_high': self.DC2pGateSweep_source_high.value(),
                'steps': int(self.DC2pGateSweep_source_steps.value()),
                'repeats': int(self.DC2pGateSweep_source_repeats.value()),
                'nplc': float(self.nplc.currentText()),
                'limit': self.source_max_current.value() * 1e-3,
            },
            'params': {
                'autozero': False,  # TODO!!!!!!!
                'readback': False,  # TODO!!!!!!!
                'source_measure_delay': 1e-3,  # TODO!!!!!!!
            },
        }
        print(command)
        if not no_execution:
            self._write_socket(command, 8510)
        return command

    def _simulate_2p_dc_gate_sweep(self):
        command = self._start_2p_dc_gate_sweep(no_execution=True)
        simulation = self._read_simulation(command)
        self.simulation_inner_line.setData(simulation['time'], simulation['inner'])
        self.simulation_outer_line.setData(simulation['time'], simulation['outer'])
        # self.updateViews()

    def _start_4p_delta_dc_gate_sweep(self):
        comment = self.measurement_comment.text()
        current = self.delta_cc_dc_gate_sweep_current.value() * 1e-6
        v_limit = self.current_source_max_voltage.value()
        v_low = self.delta_cc_dc_gate_sweep_v_low.value()
        v_high = self.delta_cc_dc_gate_sweep_v_high.value()
        v_xx_range = self.delta_cc_dc_vxx_range.value()
        steps = int(self.delta_cc_dc_gate_sweep_steps.value())
        repeats = int(self.delta_cc_dc_gate_sweep_repeats.value())
        nplc = float(self.nplc.currentText())
        if len(comment) < 5:
            self.alert('Comment too short')
            return False

        command = {
            'cmd': 'start_measurement',
            'measurement': 'delta_constant_current_gate_sweep',
            'comment': comment,
            'current': current,
            'v_limit': v_limit,
            'v_low': v_low,
            'v_high': v_high,
            'v_xx_range': v_xx_range,
            'steps': steps,
            'repeats': repeats,
            'nplc': nplc,
        }
        print(command)
        self._write_socket(command, 8510)

    def _start_4p_dc_iv_curve(self):
        comment = self.measurement_comment.text()
        v_limit = self.current_source_max_voltage.value()
        start = self.dc_iv_start_current.value() * 1e-6
        stop = self.dc_iv_end_current.value() * 1e-6
        steps = int(self.dc_iv_steps.value())
        nplc = float(self.nplc.currentText())
        gate_v = self.dc_iv_gate_v.value()
        command = {
            'cmd': 'start_measurement',
            'measurement': 'dc_4_point',
            'comment': comment,
            'start': start,
            'stop': stop,
            'steps': steps,
            'v_limit': v_limit,
            'nplc': nplc,
            'gate_v': gate_v,
        }
        print(command)
        self._write_socket(command, 8510)

    def _start_differential_conductance(self):
        comment = self.measurement_comment.text()
        v_limit = self.current_source_max_voltage.value()
        start = self.differential_conductance_start_current.value() * 1e-6
        stop = self.differential_conductance_end_current.value() * 1e-6
        delta = self.differential_conductance_delta.value() * 1e-6
        gate_v = self.differential_conductance_gate_v.value()
        steps = int(self.differential_conductance_steps.value())
        nplc = float(self.nplc.currentText())

        command = {
            'cmd': 'start_measurement',
            'measurement': 'diff_conductance',
            'comment': comment,
            'start': start,
            'stop': stop,
            'steps': steps,
            'delta': delta,
            'v_limit': v_limit,
            'nplc': nplc,
            'gate_v': gate_v,
        }
        print(command)
        self._write_socket(command, 8510)

    def _start_delta_constant_current(self):
        comment = self.measurement_comment.text()
        current = self.constant_current_delta_current.value() * 1e-6
        measure_time = self.constant_current_delta_measure_time.value()
        v_limit = self.current_source_max_voltage.value()
        gate_v = self.constant_current_delta_gate_v.value()
        if len(comment) < 5:
            self.alert('Comment too short')
            return False

        command = {
            'cmd': 'start_measurement',
            'measurement': 'delta_constant_current',
            'comment': comment,
            'current': current,
            'v_limit': v_limit,
            'gate_v': gate_v,
            # todo: nplc
            'measure_time': measure_time,
        }
        print(command)
        self._write_socket(command, 8510)

    # def _update_source_voltage(self):
    #     setpoint = self.source_voltage_setpoint.value()
    #     self._update_via_socket('source_voltageerature_setpoint', setpoint)

    def _read_socket(self, cmd, port=9000):
        self.read_socket_in_use = True
        try:
            socket_cmd = cmd + '#json'
            self.read_socket.sendto(socket_cmd.encode(), (IP, port))
            time.sleep(0.01)
            recv = self.read_socket.recv(65535).decode('ascii')
            data = json.loads(recv)
            if 'OLD' in data:
                value = None
            else:
                value = data[1]
        except BlockingIOError:
            value = None
        self.read_socket_in_use = False
        return value

    def _update_temp_and_field(self):
        # TODO:
        # Consider to move all the socket reads into a separate thread that
        # will continuously track these values
        source_voltage = self._read_socket('source_voltage')
        gate_voltage = self._read_socket('gate_voltage')
        if source_voltage is None or gate_voltage is None:
            return
        self.source_voltage_show.setText('{:.2f}mV'.format(sourc_voltage * 1000))
        self.gate_voltage_show.setText('{:.2f}mV'.format(gate_voltage * 1000))

        self.source_voltage_x.append(time.time() - self.t_start)
        self.source_voltage_y.append(source_voltage)
        self.gate_voltage_x.append(time.time() - self.t_start)
        self.gate_voltage_y.append(sample_temp)

        self.source_voltage_line.setData(self.source_voltage_x, self.source_voltage_y)
        self.gate_voltage_line.setData(self.gate_voltage_x, self.gate_voltage_y)

    def update_plot_data(self):
        if self.read_socket_in_use:
            time.sleep(0.05)
            return
        self._update_temp_and_field()

        # Read status of ongoing measurement
        status = self._read_socket('status', 9002)
        print('Status is ', status)
        measurement_type = status['type']
        print(measurement_type)
        if not measurement_type == self.latest_measurement_type:
            self.measurement_plot_x = []
            self.measurement_plot_y = []

        if measurement_type is None:
            # v_tot is just a value, not a (time, value) point
            v_tot = self._read_socket('v_tot', 9002)
            self.measurement_plot_x.append(time.time() - self.t_start)
            self.measurement_plot_y.append(v_tot)
            self.current_measurement_show.setText('No measurement')
        else:
            v_xx = self._read_socket('v_xx', 9002)
            self.current_measurement_show.setText(measurement_type)
            if v_xx is not None:
                if None not in v_xx:
                    # TODO: Could we differentiate by measurement type?
                    self.measurement_plot_x.append(v_xx[0])
                    self.measurement_plot_y.append(v_xx[1])

        if None not in (self.measurement_plot_x + self.measurement_plot_y):
            self.measurement_line.setData(
                self.measurement_plot_x, self.measurement_plot_y
            )
        self.latest_measurement_type = measurement_type


def main():
    app = QtWidgets.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
