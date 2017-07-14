
from __future__ import division, print_function

import time
import sys
import numpy as np
from qwt.qt import QtGui, QtCore
from qwt import QwtPlot, QwtPlotCurve

YS = 10
POINTS = 10000
FREQ = 10

print("Points:", POINTS)
print("Freq:", FREQ)
print("Points per s:", POINTS * FREQ)


x = np.linspace(0, 6.28, POINTS)
ys = [np.sin(x + 6.28/YS*n) for n in range(YS)]



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
        self.plot = QwtPlot("Test", self)
        self.plot.resize(900, 900)
        self.curve = QwtPlotCurve("Curve 1")
        self.curve.attach(self.plot)
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
