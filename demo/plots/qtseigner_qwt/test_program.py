"""QtDesigner test"""

import sys
import time
import random

import numpy as np
from PyQt4 import Qt, QtCore
from PyQt4.QtGui import QWidget

from simple_plot import Ui_PlotTest
from PyExpLabSys.common.plotters import DataPlotter


class SimplePlot(QWidget):
    """Simple example with a Qwt plot in a Qt GUI"""
    def __init__(self):
        super(SimplePlot, self).__init__()

        # Set up the user interface from Designer.
        self.gui = Ui_PlotTest()
        self.gui.setupUi(self)

        # Init local variables
        self.scale = 1E-8
        self.active = False
        self.start = None
        self.plot_length = 20

        # Set up plot (using pretty much all the possible options)
        self.plots_l = ['signal1', 'signal2']
        self.plots_r = ['aux_signal1']
        self.plotter = DataPlotter(
            self.plots_l, right_plotlist=self.plots_r, parent=self,
            left_log=True, title='Awesome plots',
            yaxis_left_label='Log sine, cos', yaxis_right_label='Noisy line',
            xaxis_label='Time since start [s]',
            legend='right', left_thickness=[2, 8], right_thickness=6,
            left_colors=['firebrick', 'darkolivegreen'],
            right_colors=['darksalmon'])
        self.gui.horizontalLayout.addWidget(self.plotter.plot)
        # Make the content scale with the Window
        self.setLayout(self.gui.horizontalLayout)

        # Connect signals
        QtCore.QObject.connect(self.gui.start_button,
                               QtCore.SIGNAL('clicked()'),
                               self.on_start)
        QtCore.QObject.connect(self.gui.stop_button,
                               QtCore.SIGNAL('clicked()'),
                               self.on_stop)
        QtCore.QObject.connect(self.gui.scale_spinbutton,
                               QtCore.SIGNAL('valueChanged(int)'),
                               self.on_scale)
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

    def on_stop(self):
        """Stop button method"""
        print 'stop pressed'
        self.active = False

    def on_scale(self, value):
        """Scale spin button method"""
        print 'scale change, new value'.format(self.scale)
        self.scale = 10 ** value
        self.gui.scale_label.setText('1E' + str(value))

    def plot_iteration(self):
        """method that emulates a single data gathering and plot update"""
        elapsed = time.time() - self.start
        if elapsed <= self.plot_length:

            value = (np.sin(elapsed) + 1.1) * self.scale
            self.plotter.add_point('signal1', (elapsed, value))
            value = (np.cos(elapsed) + 1.1) * self.scale
            self.plotter.add_point('signal2', (elapsed, value))
            value = elapsed + random.random()
            self.plotter.add_point('aux_signal1', (elapsed, value))
        else:
            self.active = False

        if self.active:
            # Under normal curcumstances we would not add a delay
            QtCore.QTimer.singleShot(100, self.plot_iteration)


def main():
    """Main method"""
    app = Qt.QApplication(sys.argv)
    testapp = SimplePlot()
    testapp.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
