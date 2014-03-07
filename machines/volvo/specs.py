"""QtDesigner test"""

import sys
import time
import random

import numpy as np
from PyQt4 import Qt, QtCore
from PyQt4.QtGui import QWidget

import sys
sys.path.append('/home/cinf/PyExpLabSys/PyExpLabSys/drivers')
sys.path.append('/home/cinf/PyExpLabSys/')
from sputter_gui import Ui_Specs
from PyExpLabSys.common.plotters import DataPlotter




import specs_iqe11


class SimplePlot(QWidget):
    """Simple example with a Qwt plot in a Qt GUI"""
    def __init__(self, sputtergun):
        super(SimplePlot, self).__init__()

        self.sputtergun = sputtergun

        # Set up the user interface from Designer.
        self.gui = Ui_Specs()
        self.gui.setupUi(self)

        # Init local variables
        self.scale = 1E-8
        self.active = False
        self.start = None
        self.plot_length = 200

        # Set up plot (using pretty much all the possible options)
        self.plots_l = ['filament_current', 'sputter_current']
        self.plots_r = ['temperature']
        self.plotter = DataPlotter(
            self.plots_l, right_plotlist=self.plots_r, parent=self,
            left_log=False, title='Ion Gun Data',
            yaxis_left_label='Currents', yaxis_right_label='Noisy line',
            xaxis_label='Time since start [s]',
            legend='right', left_thickness=[2, 8], right_thickness=6,
            left_colors=['firebrick', 'darkolivegreen'],
            right_colors=['darksalmon'])
        self.gui.horizontalLayout.removeWidget(self.gui.place_holder_qwt)
        self.gui.place_holder_qwt.setParent(None)
        self.gui.horizontalLayout.addWidget(self.plotter.plot)

        # Connect signals
        QtCore.QObject.connect(self.gui.operate_button,
                               QtCore.SIGNAL('clicked()'),
                               self.on_operate)        
        QtCore.QObject.connect(self.gui.standby_button,
                               QtCore.SIGNAL('clicked()'),
                               self.on_standby)        
        QtCore.QObject.connect(self.gui.start_button,
                               QtCore.SIGNAL('clicked()'),
                               self.on_start)
        QtCore.QObject.connect(self.gui.stop_button,
                               QtCore.SIGNAL('clicked()'),
                               self.on_stop)
        QtCore.QObject.connect(self.gui.quit_button,
                               QtCore.SIGNAL('clicked()'),
                               QtCore.QCoreApplication.instance().quit)

    def on_start(self):
        """Start button method"""
        print 'start pressed'
        if not self.active:
            self.start = time.time()
            self.active = True

            # Reset plot
            for key in self.plotter.data.keys():
                self.plotter.data[key] = []

            QtCore.QTimer.singleShot(0, self.plot_iteration)

    def on_standby(self):
        """Standby button method"""
        self.sputtergun.standby()

    def on_operate(self):
        """Standby button method"""
        self.sputtergun.operate()
        print "!"


    def on_stop(self):
        """Stop button method"""
        print 'stop pressed'
        self.active = False

    def plot_iteration(self):
        """method that emulates a single data gathering and plot update"""
        elapsed = time.time() - self.start
        self.gui.sputter_current.setProperty("value", self.sputtergun.status['sputter_current'])
        self.gui.filament_bias.setProperty("text", str(self.sputtergun.status['filament_bias']))
        self.gui.temp_energy_module.setProperty("text", str(self.sputtergun.status['temperature']))
        self.gui.filament_current.setProperty("text", str(self.sputtergun.status['filament_current']))
        self.gui.accel_voltage.setProperty("text", str(self.sputtergun.status['accel_voltage']))
        self.gui.emission_current.setProperty("text", str(self.sputtergun.status['emission_current']))

        if elapsed <= self.plot_length:
            self.plotter.add_point('sputter_current', (elapsed, self.sputtergun.status['sputter_current']))
            print self.sputtergun.status['sputter_current']
            value = (np.sin(elapsed) + 1.1) * self.scale
            self.plotter.add_point('filament_current', (elapsed, self.sputtergun.status['filament_current']))
            value = (np.cos(elapsed) + 1.1) * self.scale
            self.plotter.add_point('temperature', (elapsed, self.sputtergun.status['temperature']))
        else:
            self.active = False

        if self.active:
            # Under normal curcumstances we would not add a delay
            QtCore.QTimer.singleShot(100, self.plot_iteration)


def main():
    """Main method"""
    sputtergun = specs_iqe11.Puiqe11(simulate=True)
    sputtergun.start()

    app = Qt.QApplication(sys.argv)
    testapp = SimplePlot(sputtergun)
    testapp.show()
    #sys.exit(app.exec_()) #Ask Kenneth about this construction
    app.exec_()
    sputtergun.running = False

if __name__ == '__main__':

    main()
