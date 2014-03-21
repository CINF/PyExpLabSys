import sys
import time
import random

import numpy as np
from PyQt4 import Qt, QtGui, QtCore

from PyExpLabSys.common.plotters import DataPlotter


class TestApp(QtGui.QWidget):
    """Test Qt application"""

    def __init__(self):
        super(TestApp, self).__init__()
        # Form plotnames
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

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.plotter.plot)
        self.setLayout(hbox)
        self.setGeometry(5, 5, 500, 500)

        self.start = time.time()
        QtCore.QTimer.singleShot(10, self.main)

    def main(self):
        """Simulate gathering one set of points and adding them to plot"""
        elapsed = time.time() - self.start
        value = (np.sin(elapsed) + 1.1) * 1E-9
        self.plotter.add_point('signal1', (elapsed, value))
        value = (np.cos(elapsed) + 1.1) * 1E-8
        self.plotter.add_point('signal2', (elapsed, value))
        value = elapsed + random.random()
        self.plotter.add_point('aux_signal1', (elapsed, value))

        QtCore.QTimer.singleShot(100, self.main)


def main():
    """Main method"""
    app = Qt.QApplication(sys.argv)
    testapp = TestApp()
    testapp.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
