#!/usr/bin/env python

import gtk
import gobject

import random
import time
import numpy

from LivePlotsRunning import NPointRunning

class StatusWindow:
    """ An example implementation of a status window.
    
    To make a real implementation it is necessary to edit the plot definition
    and add data reading code to the new_data_point method
    """

    def __init__(self):
        """ Initate the gui """
        # Build the GUI and connect signals
        self.builder = gtk.Builder()
        self.builder.add_from_file(
            "gui/example_implementation_status_window.glade")
        self.builder.connect_signals(self)

        # Assign important widgets to variables
        self.vbox = self.builder.get_object('vbox')
        self.win = self.builder.get_object('window1')

        self.nlines = [1, 1, 1, 5, 6, 8]
        # Make one list with all the plots
        self.plots = [
                NPointRunning(number_of_lines=1, number_of_points=10,
                              title='Static y-scale', y_bounds=[0.5, 10]),
                NPointRunning(number_of_lines=1, number_of_points=50),
                NPointRunning(number_of_lines=1, number_of_points=100),
                NPointRunning(number_of_lines=5, number_of_points=100,
                              legends = ['a', 'b', 'c', 'd', 'e'],
                              legend_placement='top', legend_cols=5),
                NPointRunning(number_of_lines=6, number_of_points=100,
                              legends = ['a', 'b', 'c', 'd', 'e', 'f'],
                              legend_placement='left', logscale=True,
                              title='Logscale', line_colors=
                              [str(col) for col in numpy.arange(0.3, 1, 0.13)]),
                NPointRunning(number_of_lines=8, number_of_points=100,
                              legends = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'],
                              legend_placement='left', title='plain'),
                ]

        # list length is rows, items are number of plots in row
        self.layout = [3, 1, 2]
        if sum(self.layout) != len(self.plots):
            raise Exception("Total number of plots must match sum of integers "
                            "in layout")
        # Fill the plots in the layout
        plot = 0
        for plot_in_row in self.layout:
            hbox = gtk.HBox()
            for n in range(plot_in_row):
                hbox.pack_start(self.plots[plot])
                plot += 1
            self.vbox.pack_start(hbox)
        
        self.win.show_all()
        gobject.idle_add(self.new_data_point)
        gtk.main()

    def new_data_point(self):
        """ Add new data points to the plots """
        for plot, lines in zip(self.plots, self.nlines):
            dat = []
            #base = numpy.sin(time.time()*0.1)
            base = 1
            for line in range(lines):
                dat.append(base + random.random()*0.1)
            plot.push_new_points(dat)
            
        for n in range(1, 4):
            self.builder.get_object('label{0}'.format(n)).\
                set_label(str(random.random()))
        time.sleep(1)
        return True
    
    def on_window_destroy(self, widget):
        """ Window destroy """
        gtk.main_quit()

if __name__ == "__main__":
    n_point_running_test = StatusWindow()
