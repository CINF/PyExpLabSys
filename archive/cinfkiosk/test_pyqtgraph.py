from __future__ import division, print_function

import time
import sys
import numpy as np

from pyqtgraph import PlotWidget, AxisItem

from PyQt4 import QtGui, QtCore

YS = 10
POINTS = 10000
FREQ = 10

print("Points:", POINTS)
print("Freq:", FREQ)
print("Points per s:", POINTS * FREQ)


x = np.linspace(0, 6.28, POINTS)
ys = [np.sin(x + 6.28/YS*n) for n in range(YS)]


class TimeAxisItem(AxisItem):
    def __init__(self, *args, **kwargs):
        super(TimeAxisItem, self).__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        """Return HH:mm:ss strings from unixtime values"""
        #out = []
        #for value in values:
        #    t = QDateTime()
        #    t.setTime_t(value)
        #    out.append(t.toString('HH:mm:ss'))
        return [str(value) for value in values]


class Example(QtGui.QWidget):
    
    def __init__(self):
        super(Example, self).__init__()        
        self.initUI()


        self.current_y = 0

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.setInterval(1000/FREQ)
        self.timer.start()
        
        
    def initUI(self):
        
        self.setGeometry(300, 300, 1000, 1000)
        self.setWindowTitle('Icon')
        self.setWindowIcon(QtGui.QIcon('web.png'))



        self.plot = PlotWidget(self, axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self.plot.resize(900, 900)
        self.curve = self.plot.plot(x, ys[0])
        #self.curve.attach(self.plot)
        self.show()

    def update_plot(self):
        self.curve.setData(x, ys[self.current_y])
        self.current_y = (self.current_y + 1) % YS
        #print(POINTS * FREQ, "points per second")
        
        
def main():
    
    app = QtGui.QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()    
