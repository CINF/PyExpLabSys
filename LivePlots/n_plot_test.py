#!/usr/bin/env python

import gtk
import gobject

import random
import time
import numpy

from LivePlotsRunning import NPointRunning

class NPointRunningTest:
    """ A simple gui to test the NPointRunning plot class """

    def __init__(self):
        """ Initate the gui """
        # Build the GUI and connect signals
        self.builder = gtk.Builder()
        self.builder.add_from_file("gui/test_gui.glade")
        self.builder.connect_signals(self)

        # Assign important widgets to variables
        self.win = self.builder.get_object('window')

        self.nlines = 3
        # Add a matplotlib graph
        self.plot = NPointRunning(number_of_lines=self.nlines,
                                  #line_styles=['b', 'r', 'g'],
                                  #line_colors=['blue', 'red', 'green'],
                                  title='Handsome test plot',
                                  x_label='Points',
                                  y_label='Sine plus noise',
                                  legends=['Sine {0}'.format(n)\
                                               for n in range(self.nlines)],
                                  legend_cols=3,
                                  legend_placement='top',
                                  )
        self.win.add(self.plot)
        self.win.show_all()
        gobject.idle_add(self.new_data_point)
        gtk.main()

    def new_data_point(self):
        data = [numpy.sin(time.time()*0.1+n)+random.random()*0.1\
                    for n in range(self.nlines)]
        self.plot.push_new_points(data)
        time.sleep(0.1)
        return True
    
    def on_window_destroy(self, widget):
        """ Window destroy """
        gtk.main_quit()

if __name__ == "__main__":
    n_point_running_test = NPointRunningTest()
