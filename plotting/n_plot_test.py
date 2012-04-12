#!/usr/bin/env python

import gtk
import gobject

import random
import time

from running_plots import NPointRunning

class NPointRunningTest:
    """ A simple gui to test the NPointRunning plot class """

    def __init__(self):
        """ Initate the gui """
        # Build the GUI and connect signals
        self.builder = gtk.Builder()
        self.builder.add_from_file("test_gui.glade")
        self.builder.connect_signals(self)

        # Assign important widgets to variables
        self.win = self.builder.get_object('window')

        # Add a matplotlib graph
        self.plot = NPointRunning(100, 2, legends=['a', 'b'], logscale=True)
        self.win.add(self.plot)

        self.win.show_all()
        gobject.idle_add(self.new_data_point)


    def new_data_point(self):
        self.plot.push_new_point([random.random()+0.1,random.random()+0.1])
        time.sleep(0.1)
        return True

    def on_window_destroy(self, widget):
        """ Window destroy """
        gtk.main_quit()

if __name__ == "__main__":
    n_point_running_test = NPointRunningTest()
    gtk.main()
