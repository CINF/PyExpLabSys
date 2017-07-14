import sys

import numpy as np
from pyqtgraph import PlotWidget, AxisItem
from PyQt4 import QtGui, QtCore


class TimeAxisItem(AxisItem):
    """Only included to show that the point is to subclass"""


class Example(QtGui.QWidget):
    def __init__(self):
        super(Example, self).__init__()        
        self.setGeometry(300, 300, 400, 400)
        self.plot = PlotWidget(self, axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.plot.resize(300, 300)
        self.curve = self.plot.plot(np.linspace(0, 10, 100), np.random.random(100))
        self.show()


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())
