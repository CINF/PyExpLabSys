"""QtDesigner test"""

import sys

from PyQt4 import Qt, QtCore
import PyQt4

from testui import Ui_PlotTest
from PyExpLabSys.common.plotters import DataPlotter


class SimplePlot(PyQt4.QtGui.QWidget):
    def __init__(self):
        #QWidget.__init__(self)
        super(SimplePlot, self).__init__()

        # Set up the user interface from Designer.
        self.ui = Ui_PlotTest()
        self.ui.setupUi(self)

        self.scale = 1E-8

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
        self.ui.horizontalLayout.addWidget(self.plotter.plot)
        # Make some local modifications.
        #self.ui.colorDepthCombo.addItem("2 colors (1 bit per pixel)")

        # Connect up the buttons.
        QtCore.QObject.connect(self.ui.start_button, QtCore.SIGNAL('clicked()'),
                               self.on_start)
        QtCore.QObject.connect(self.ui.stop_button, QtCore.SIGNAL('clicked()'),
                               self.on_stop)
        #QtCore.QObject.connect(self.ui.scale_spinbutton, QtCore.SIGNAL('onvalueChanged()'),
        #        self.scale)
        self.ui.scale_spinbutton.valueChanged.connect(self.on_scale)

    def on_start(self):
        print 'start'

    def on_stop(self):
        print 'stop'

    def on_scale(self, value):
        self.scale = 10 ** value
        self.ui.scale_label.setText('1E' + str(value))
        print self.scale


def main():
    """Main method"""
    app = Qt.QApplication(sys.argv)
    testapp = SimplePlot()
    testapp.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
