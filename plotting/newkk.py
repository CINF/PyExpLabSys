#!/usr/bin/env python
# -*- coding: utf-8 -*-

import matplotlib
matplotlib.use('GTKAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as\
    FigureCanvas

import gtk
import gobject

from agilent_34410A import Agilent34410ADriver

import time
import random

class Multimeter:
    """Small Agilent Multimeter Program"""

    def __init__(self):
        """ Initialisation of driver and gui """

        self.device = Agilent34410ADriver()

        self.builder = gtk.Builder()
        self.builder.add_from_file("test_gui.glade")
        self.x = []
        self.y = []
        self.update_timer = None
        self.starttime = time.time()

        fig = Figure(figsize=(5, 4), dpi=100)
        fig.set_facecolor('white')
        self.ax = fig.add_subplot(111)
        #self.line, = self.ax.plot(self.x, self.y, 'b')

        self.canvas = FigureCanvas(fig)
        self.builder.get_object('hbox1').add(self.canvas)


        self.update_timer = gobject.idle_add(self.update)
        #self.builder.connect_signals(self)

    def set_update(self, widget=None, state=True):
        """ Method to toggle whether we are asking for measurement for
        measurements and updating the graph
        """
        if widget is not None:
            active = widget.get_active()
        else:
            active = state

        if self.update_timer is None and active:
            self.update_timer = gobject.idle_add(self.update)
        elif self.update_timer is not None and not active:
            gobject.source_remove(self.update_timer)
            self.update_timer = None

    def update(self):
        """ Ask for measurement and update graph """
        new_measurement = self.random.random()
        self.x.append(time.time() - self.starttime)
        self.y.append(new_measurement)
        self.x = self.x[self.points * -1:]
        self.y = self.y[self.points * -1:]
        self.ax.clear()
        self.ax.plot(self.x, self.y, 'b')
        #self.ax.plot([time.time() - self.starttime], [new_measurement], 'b')
        #self.line.set_data(self.x, self.y)
        self.canvas.draw()
        return True

    def on_window_destroy(self, widget):
        """ Mandatory gui method to quit when the window is destroyed """
        gtk.main_quit()

if __name__ == "__main__":
    t = Multimeter()
    t.win.show_all()
    gtk.main()
