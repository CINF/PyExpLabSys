# pylint: disable=E1101, E0611
#! /usr/bin/python
"""QtDesigner test"""
from __future__ import print_function
import sys
import time
import threading
import socket
import pickle
from PyQt4 import Qt, QtCore
from PyQt4.QtGui import QWidget
from temperature_controller_gui_2 import Ui_temp_control
from PyExpLabSys.common.plotters import DataPlotter
from PyExpLabSys.common.supported_versions import python2_only
import temperature_controller_config as config
python2_only(__file__)


class TemperatureControllerComm(threading.Thread):
    """ Communicates with temperature controller over network """
    def __init__(self):
        threading.Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.5)
        self.running = True
        self.status = {}
        self.status['temperature'] = 0
        self.status['setpoint'] = 0
        self.status['dutycycle'] = 0
        self.status['connected'] = False
        self.status['temp_connected'] = False

    def read_param(self, param):
        """ Read a parameter from the controller """
        data = param + '#raw'
        error = 1
        # TODO: Investigate the reason for these network errors
        while (error < 50) and (error > 0):
            time.sleep(0.1)
            self.sock.sendto(data, (config.controller_hostname, config.controller_pull_port))
            received = self.sock.recv(1024)
            try:
                value = float(received[received.find(',') + 1:])
                error = 0
                #print 'Error: ' + str(error)
            except ValueError:
                error = error + 1
                #print 'Error: ' + str(error)
                value = -1
        return value

    def run(self):
        while self.running is True:
            try:
                self.status['temperature'] = self.read_param('temperature')
                self.status['temp_connected'] = True
            except socket.error:
                self.status['temp_connected'] = False
            try:
                self.status['dutycycle'] = self.read_param('dutycycle')
                print(self.status['dutycycle'])
                self.status['setpoint'] = self.read_param('setpoint')
                self.status['connected'] = True
            except socket.error:
                self.status['connected'] = False
            if not self.status['temp_connected']:
                self.status['connected'] = False
            time.sleep(0.2)


class SimplePlot(QWidget):
    """Simple example with a Qwt plot in a Qt GUI"""
    def __init__(self, temp_control_comp):
        super(SimplePlot, self).__init__()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.5)

        self.tcc = temp_control_comp

        # Set up the user interface from Designer.
        self.gui = Ui_temp_control()
        self.gui.setupUi(self)

        # Init local variables
        self.scale = 1E-8
        self.active = False
        self.start = None
        self.ramp_start = 0
        self.ramp = {}
        self.ramp['time'] = {}
        self.ramp['temp'] = {}
        self.ramp['step'] = {}
        # Set up plot (using pretty much all the possible options)
        self.plots_l = ['temperature', 'setpoint']
        self.plots_r = ['dutycycle']
        self.plotter = DataPlotter(
            self.plots_l, right_plotlist=self.plots_r, parent=self,
            left_log=False, title='Temperature control',
            yaxis_left_label='Temperature', yaxis_right_label='Dutycycle',
            xaxis_label='Time since start [s]',
            legend='right', left_thickness=[2, 3], right_thickness=2,
            left_colors=['firebrick', 'darkolivegreen'],
            right_colors=['darksalmon'])
        self.gui.horizontalLayout.removeWidget(self.gui.place_holder_qwt)
        self.gui.place_holder_qwt.setParent(None)
        self.gui.horizontalLayout.addWidget(self.plotter.plot)

        # Connect signals
        QtCore.QObject.connect(self.gui.start_ramp_button,
                               QtCore.SIGNAL('clicked()'),
                               self.on_start_ramp)
        QtCore.QObject.connect(self.gui.stop_ramp_button,
                               QtCore.SIGNAL('clicked()'),
                               self.on_stop_ramp)
        QtCore.QObject.connect(self.gui.start_button,
                               QtCore.SIGNAL('clicked()'),
                               self.on_start)
        QtCore.QObject.connect(self.gui.stop_button,
                               QtCore.SIGNAL('clicked()'),
                               self.on_stop)
        QtCore.QObject.connect(self.gui.quit_button,
                               QtCore.SIGNAL('clicked()'),
                               QtCore.QCoreApplication.instance().quit)
        QtCore.QObject.connect(self.gui.new_setpoint,
                               QtCore.SIGNAL('returnPressed()'),
                               self.update_setpoint)
    def on_start(self):
        """Start button method"""
        print('<< start pressed >>')
        if not self.active:
            self.start = time.time()
            self.active = True
            # Reset plot
            for key in self.plotter.data.keys():
                self.plotter.data[key] = []
            QtCore.QTimer.singleShot(0, self.plot_iteration)
        else:
            print('...already running!')

    def update_setpoint(self):
        """Update setpoint button method"""
        print('<< Updating setpoint >>')
        new_setpoint = self.gui.new_setpoint.text()
        try:
            float(new_setpoint)
        except ValueError:
            message = '...ValueError: {}\nOriginal setpoint used instead.'.format(repr(new_setpoint))
            new_setpoint = str(self.tcc.status['setpoint'])
            print(message)
        self.gui.new_setpoint.setProperty("text", new_setpoint)
        data = 'raw_wn#setpoint:float:' + str(new_setpoint)
        self.sock.sendto(data, (config.controller_hostname, config.controller_push_port))
        received = self.sock.recv(1024)
        print(received)


    def on_start_ramp(self):
        """Start temperature ramp"""
        print('<< Start ramp pressed >>')
        print('Current ramp settings:')
        print(self.ramp)
        self.ramp_start = time.time()
        for i in range(0, 11):
            self.ramp['time'][i] = int(self.gui.temperature_ramp.item(i, 0).text())
            self.ramp['temp'][i] = int(self.gui.temperature_ramp.item(i, 1).text())
            self.ramp['step'][i] = int(self.gui.temperature_ramp.item(i, 2).checkState()) == 2
        data = 'raw_wn#ramp:str:' +  pickle.dumps(self.ramp)
        print(data)
        self.sock.sendto(data, (config.controller_hostname, config.controller_push_port))
        received = self.sock.recv(1024)
        print(received)
        print('New ramp settings:')
        print(self.ramp)

    def on_stop_ramp(self):
        """Stop temperature ramp"""
        print('<< Stop ramp pressed >>')
        data = 'raw_wn#ramp:str:stop'
        self.sock.sendto(data, (config.controller_hostname, config.controller_push_port))
        received = self.sock.recv(1024)
        print(received)

    def on_stop(self):
        """Stop button method"""
        print('<< Stop pressed >>')
        self.active = False

    def plot_iteration(self):
        """method that emulates a single data gathering and plot update"""
        elapsed = time.time() - self.start
        if self.tcc.status['connected'] is True:
            self.gui.temperature.setProperty("text", str(self.tcc.status['temperature']) + 'C')
            self.gui.power.setProperty("text", str(self.tcc.status['dutycycle']) + 'W')
            self.gui.setpoint.setProperty("text", str(self.tcc.status['setpoint']) + 'C')

        else:
            self.gui.current.setProperty("text", '-')
            self.gui.voltage.setProperty("text", '-')
            self.gui.temperature.setProperty("text", '-')
            self.gui.power.setProperty("text", '-')
            self.gui.resistance.setProperty("text", '-')
            self.gui.setpoint.setProperty("text", '-')
        try:
            if self.tcc.status['temp_connected'] is True:
                self.plotter.add_point('temperature',
                                       (elapsed, self.tcc.status['temperature']))
            if self.tcc.status['connected'] is True:
                self.plotter.add_point('setpoint', (elapsed, self.tcc.status['setpoint']))
                self.plotter.add_point('dutycycle', (elapsed, self.tcc.status['dutycycle']))
        except TypeError:
            pass

        if self.active:
            # Under normal curcumstances we would not add a delay
            QtCore.QTimer.singleShot(500, self.plot_iteration)


def main():
    """Main method"""
    tcc = TemperatureControllerComm()
    tcc.start()

    app = Qt.QApplication(sys.argv)
    testapp = SimplePlot(tcc)
    testapp.show()
    app.exec_()
    tcc.running = False

if __name__ == '__main__':

    main()
