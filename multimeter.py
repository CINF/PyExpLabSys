#!/usr/bin/env python
# -*- coding: utf-8 -*-


import matplotlib
matplotlib.use('GTK')
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
        self.builder.add_from_file("gui.glade")
        self.x = []
        self.y = []
        self.update_timer = None
        self.starttime = time.time()

        name = self.device.readSoftwareVersion(short=True)
        self.win = self.builder.get_object('window1')
        self.win.set_title(name) # SUBS with name from driver

        fig = Figure(figsize=(5, 4), dpi=100)
        fig.set_facecolor('white')
        self.ax = fig.add_subplot(111)
        self.canvas = FigureCanvas(fig)
        hbox = self.builder.get_object('hbox1')
        hbox.pack_start(self.canvas)
        hbox.reorder_child(self.canvas, 0)

        types = ['Bias [V]', 'Current [A]', 'Resistance [Ohm]']
        type_combo = self.build_combo('combobox1', types)

        resistances = ['Input Impedance LOW', 'Input Impedance AUTO HIGH']
        self.resistance_combo = self.build_combo('combobox2', resistances)

        frequences = ['As fast as possible', '10 Hz', '5 Hz', '2 Hz', '1 Hz']
        frequency_combo = self.build_combo('combobox3', frequences)
        self.update_interval = -1

        n_points = ['10 points', '20 points', '50 points', '100 points']
        n_points_combo = self.build_combo('combobox4', n_points)
        self.points = 10

        type_combo.set_active(0)
        self.resistance_combo.set_active(0)
        self.device.setAutoInputZ(False)
        frequency_combo.set_active(0)
        n_points_combo.set_active(3)

        self.builder.connect_signals(self)

    def build_combo(self, widget_name, options):
        """ Convenience method to create a combobox """
        # Comboboxes are not nice in GTK, or I'm to tired to figure out how to
        # them in a nice way
        combo = self.builder.get_object(widget_name)
        liststore = gtk.ListStore(gobject.TYPE_STRING)
        for item in options:
            liststore.append([item])
        combo.set_model(liststore)
        cell = gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, "text", 0)
        return combo

    def on_combobox1_changed(self, widget):
        """ Method that handles changes in what is measured """
        before = self.builder.get_object('toggle_update').get_active()
        self.set_update(None, False)
        model = widget.get_model()
        active = widget.get_active()
        if active >= 0:
            selection = model[active][0]
            if selection == 'Bias [V]':
                self.resistance_combo.set_sensitive(True)
                self.device.selectMeasurementFunction('VOLTAGE')
            elif selection == 'Current [A]':
                self.resistance_combo.set_sensitive(False)
                self.device.selectMeasurementFunction('CURRENT')
            elif selection == 'Resistance [Ohm]':
                self.resistance_combo.set_sensitive(False)
                self.device.selectMeasurementFunction('RESISTANCE')
        self.set_update(None, before)

    def on_combobox2_changed(self, widget):
        """ Method that handles changes in the internal resistance for bias
        measurements
        """
        before = self.builder.get_object('toggle_update').get_active()
        self.set_update(None, False)
        model = widget.get_model()
        active = widget.get_active()
        if active >= 0:
            selection = model[active][0]
            if selection == 'Input Impedance LOW':
                self.device.setAutoInputZ(False)
            elif selection == 'Input Impedance AUTO HIGH':
                print 'test'
                self.device.setAutoInputZ(True)
        self.set_update(None, before)

    def on_combobox3_changed(self, widget):
        """ Method that handles changes in the measurements speed """
        model = widget.get_model()
        active = widget.get_active()
        if active >= 0:
            selected = model[active][0]
            if selected == 'As fast as possible':
                self.update_interval = -1
            else:
                frequency = int(selected.split(' ')[0])
                self.update_interval = 1.0 / frequency

    def on_combobox4_changed(self, widget):
        """ Method that handles changes in the number of points """
        model = widget.get_model()
        active = widget.get_active()
        if active >= 0:
            selected = model[active][0]
            self.points = int(selected.split(' ')[0])

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
        start = time.time()
        new_measurement = self.device.read()
        self.builder.get_object('label_measurement').\
            set_text(str(new_measurement))
        self.x.append(time.time() - self.starttime)
        self.y.append(new_measurement)
        self.x = self.x[self.points * -1:]
        self.y = self.y[self.points * -1:]
        self.ax.clear()
        self.ax.plot(self.x, self.y, 'b')
        self.canvas.draw()
        delta = time.time() - start
        if delta < self.update_interval:
            time.sleep(self.update_interval - delta)
        return True

    def on_window_destroy(self, widget):
        """ Mandatory gui method to quit when the window is destroyed """
        gtk.main_quit()

if __name__ == "__main__":
    t = Multimeter()
    t.win.show_all()
    gtk.main()
