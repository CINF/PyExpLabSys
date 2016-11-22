from __future__ import division, print_function

import sys
import numpy as np

from pyqtgraph import PlotWidget, AxisItem

from PyQt4 import QtGui, QtCore

YS = 10
POINTS = 100000
FREQ = 10
CHUNKS = 100


""" RESULTS
COMPLETE
update_plot, 363 call(s), this call: 1.23e-03s, on avg: 7.53e-04s, total: 2.73e-01s
Points: 100000
Freq: 10
Points per s: 1.00e+06

BLOCKED
update_plot, 894 call(s), this call: 6.11e-04s, on avg: 5.62e-04s, total: 5.03e-01s
Points: 100000
Freq: 10
Points per s: 1.00e+06


"""


print("Points:", POINTS)
print("Freq:", FREQ)
print("Points per s: {:.2e}".format(POINTS * FREQ))

from time import time

OUT = '{}, {} call(s), this call: {:.2e}s, on avg: {:.2e}s, total: {:.2e}s'

def timeme(function):
    timings = []
    def inner_function(*args, **kwargs):
        start = time()
        return_value = function(*args, **kwargs)
        timings.append(time() - start)
        total = sum(timings)
        print(OUT.format(function.__name__, len(timings), timings[-1], total/len(timings), total))
        return return_value
    return inner_function


x = np.linspace(0, 6.28, POINTS)
chunksize = POINTS // CHUNKS
chunkedx = [np.array(x[s: s + chunksize]) for s in range(0, POINTS, chunksize)]
y = np.sin(x)
chunkedy = [np.array(y[s: s + chunksize]) for s in range(0, POINTS, chunksize)]

ys_large = [np.sin(x + 6.28/YS*n) for n in range(YS)]

small_x = np.array(x[POINTS-chunksize:])
ys = [large_y[POINTS-chunksize:] for large_y in ys_large]




class Example(QtGui.QWidget):
    
    def __init__(self):
        super(Example, self).__init__()        
        self.initUI()


        self.current_y = 0

        #self.timer = QtCore.QTimer()
        #self.timer.timeout.connect(self.update_plot)
        #self.timer.setInterval(1000/FREQ)
        #self.timer.start()
        
        
    def initUI(self):
        
        self.setGeometry(300, 300, 1000, 1000)
        self.setWindowTitle('Icon')
        self.setWindowIcon(QtGui.QIcon('web.png'))



        self.plot = PlotWidget(self)
        self.plot.resize(900, 900)
        self.curves = []
        for x, y in zip(chunkedx, chunkedy):
            print('plot', len(x), len(y))
            self.curves.append(self.plot.plot(x, y))
        print(self.curves[-1])
        self.show()

    @timeme
    def update_plot(self):
        self.curves[-1].setData(small_x, ys[self.current_y])
        self.current_y = (self.current_y + 1) % YS
        
        
def main():
    
    app = QtGui.QApplication(sys.argv)
    ex = Example()

    ret = app.exec_()

    print("Points:", POINTS)
    print("Freq:", FREQ)
    print("Points per s: {:.2e}".format(POINTS * FREQ))

    sys.exit(ret)


if __name__ == '__main__':
    main()    
