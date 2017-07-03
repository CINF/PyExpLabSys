#! /usr/bin/python
"""Simple gui for PyExpLabSys temperature controller"""
from __future__ import print_function
import sys
import time
import random
import threading
import socket 
import json
import pickle
import numpy as np
from PyQt4 import Qt, QtCore
from PyQt4.QtGui import QWidget
from temperature_controller_gui import Ui_temp_control
from PyExpLabSys.common.plotters import DataPlotter
import temperature_controller_config as config

class TemperatureControllerComm(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.host = 'rasppi04'
        self.running = True
        self.status = {}
        self.status['temperature'] = 0
        self.status['setpoint'] = 0
        self.status['voltage'] = 0
        self.status['current'] = 0
        self.status['power'] = 0
        self.status['resistance'] = 0
        self.status['connected'] = False
        self.status['temp_connected'] = False

    def read_param(self, param, host, port):
        data = param + '#raw'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.2)
        sock.sendto(data, (host, port))
        received = sock.recv(1024)
        try:
            value = float(received[received.find(',') + 1:])
        except ValueError:
            value = -1
        return(value)

    def run(self):
        while self.running is True:
            try:
                self.status['temperature'] = self.read_param('temperature') 
                self.status['temp_connected'] = True
            except socket.error:
                self.status['temp_connected'] = True
            try:
                self.status['power'] = self.read_param('power', port=9001)
                self.status['setpoint'] = self.read_param('setpoint', port=9001)
                self.status['voltage'] = self.read_param('voltage', port=9001)
                self.status['current'] = self.read_param('current', port=9001)
                self.status['resistance'] = self.read_param('resistance', port=9001)
                self.status['connected'] = True
            except (socket.error, ValueError):
                self.status['connected'] = False
            if not self.status['temp_connected']:
                self.status['connected'] = False
            if self.status['power'] == -1:
                self.status['connected'] = False
            time.sleep(0.2)

class SimplePlot(QWidget):
    """Simple example with a Qwt plot in a Qt GUI"""
    def __init__(self, temp_control_comp):
        super(SimplePlot, self).__init__()
        self.controller_hostname = config.controller_hostname
        self.controller_pull_port = config.controller_pull_port
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
        self.plots_r = ['power']
        self.plotter = DataPlotter(
            self.plots_l, right_plotlist=self.plots_r, parent=self,
            left_log=False, title='Temperature control',
            yaxis_left_label='Temperature', yaxis_right_label='Power',
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
        print('start pressed')
        if not self.active:
            self.start = time.time()
            self.active = True
            # Reset plot
            for key in self.plotter.data.keys():
                self.plotter.data[key] = []

            QtCore.QTimer.singleShot(0, self.plot_iteration)

    def update_setpoint(self):
        """Standby button method"""
        new_setpoint = self.gui.new_setpoint.text()
        try:
            float(new_setpoint)
        except ValueError:
            new_setpoint = str(self.tcc.status['setpoint'])
        self.gui.new_setpoint.setProperty("text", new_setpoint)
        data = 'setpoint' + str(new_setpoint)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.2)
        sock.sendto(data, (self.controller_hostname, self.controller_pull_port))
        received = sock.recv(1024)


    def on_start_ramp(self):
        """Start temperature ramp"""
        self.ramp_start = time.time()
        for i in range(0,11):
            self.ramp['time'][i] = int(self.gui.temperature_ramp.item(i,0).text())
            self.ramp['temp'][i] = int(self.gui.temperature_ramp.item(i,1).text())
            self.ramp['step'][i] = int(self.gui.temperature_ramp.item(i,2).checkState()) == 2
        data = 'ramp' +  pickle.dumps(self.ramp)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.2)
        sock.sendto(data, (self.controller_hostname, self.controller_pull_port))
        received = sock.recv(1024)

    def on_stop_ramp(self):
        """Start temperature ramp"""
        data = 'stop_ramp'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.2)
        sock.sendto(data, (self.controller_hostname, self.controller_pull_port))
        received = sock.recv(1024)

    def on_stop(self):
        """Stop button method"""
        print 'stop pressed'
        self.active = False

    def plot_iteration(self):
        """method that emulates a single data gathering and plot update"""
        elapsed = time.time() - self.start
        if self.tcc.status['connected'] is True:
            self.gui.current.setProperty("text", str(self.tcc.status['current']) + 'A')
            self.gui.voltage.setProperty("text", str(self.tcc.status['voltage']) + 'V')
            self.gui.temperature.setProperty("text", str(self.tcc.status['temperature']) + 'C')
            self.gui.power.setProperty("text", str(self.tcc.status['power']) + 'W')
            self.gui.resistance.setProperty("text", '{0:.3f}Ohm'.format(self.tcc.status['resistance']))
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
                self.plotter.add_point('temperature', (elapsed, self.tcc.status['temperature']))
            if self.tcc.status['connected'] is True:
                self.plotter.add_point('setpoint', (elapsed, self.tcc.status['setpoint']))
                self.plotter.add_point('power', (elapsed, self.tcc.status['power']))
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
