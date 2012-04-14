#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk

from matplotlib.numerix import arange, sin, pi
import matplotlib
matplotlib.use('GTKAgg')
matplotlib.interactive(True)
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas
from matplotlib.axes import Subplot
from matplotlib.figure import Figure


class GTKFacePlot (gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self,gtk.WINDOW_TOPLEVEL)

        self.set_title("MixedEmotions")
        self.set_border_width(10)
        
        self.fig = Figure(figsize=(3,1), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.x = arange(0,2*pi,0.01)           # x-array
        self.lines = self.ax.plot(self.x,sin(self.x))
        self.canvas = FigureCanvas(self.fig)
        self.add(self.canvas)      

        self.figcount = 0
        gtk.timeout_add(100, self.updatePlot)

    def updatePlot(self):
        self.figcount += 1
        self.lines[0].set_ydata(sin(self.x+self.figcount/10.0))
        self.canvas.draw()
        return gtk.TRUE


def main():
    fp = GTKFacePlot()
    fp.show_all()
    fp.connect("destroy", gtk.main_quit)
    gtk.main()

if __name__ == "__main__":
    main()
