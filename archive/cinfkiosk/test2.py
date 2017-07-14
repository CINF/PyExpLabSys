from qwt.qt.QtGui import QApplication
from qwt import QwtPlot, QwtPlotCurve
import numpy as np

app = QApplication([])

x = np.linspace(-10, 10, 500)
y1, y2 = np.cos(x), np.sin(x)

my_plot = QwtPlot("Two curves")
curve1, curve2 = QwtPlotCurve("Curve 1"), QwtPlotCurve("Curve 2")
curve1.setData(x, y1)
curve2.setData(x, y2)
curve1.attach(my_plot)
curve2.attach(my_plot)
my_plot.resize(600, 300)
my_plot.replot()
my_plot.show()

app.exec_()
