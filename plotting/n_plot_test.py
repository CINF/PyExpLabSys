#!/usr/bin/env python

import gtk
import gobject

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
        self.plot = NPointRunning(100)
        self.win.add(self.plot.canvas)

    def on_window_destroy(self, widget):
        """ Window destroy """
        gtk.main_quit()

    def update(self):
        gobject.idle_add(self.tt)

    def tt(self):
        print 'hh'

if __name__ == "__main__":
    print 'start'
    n_point_running_test = NPointRunningTest()
    print '2'
    n_point_running_test.win.show_all()
    print '3'
    gtk.main()
    print 'before'
    n_point_running_test.update()
