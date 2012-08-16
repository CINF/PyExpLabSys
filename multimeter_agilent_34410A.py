#!/usr/bin/env python
# -*- coding: utf-8 -*-

from LivePlots.LivePlotsRunning import NPointRunning
from agilent_34410A import Agilent34410ADriver
import gtk
import gobject
import time


class Multimeter:
    """Small Agilent Multimeter Program"""

    def __init__(self):
        """ Initialisation of driver and gui """

        # Get devide
        self.device = Agilent34410ADriver()

        # Load gui
        self.builder = gtk.Builder()
        self.builder.add_from_file('gui/multimeter_agilent_34410A.glade')
        # Update win title
        name = self.device.ReadSoftwareVersion(short=True)
        self.win = self.gui('window1')
        self.win.set_title(name)  # Set title: Name from driver

        # Initiate variables
        self.update_timer = None
        self.update_interval = None
        self.number_format = self.gui('entry_format').get_text()

        # Read default n_points from the gui
        points = int(self.gui('spinbutton_points').get_value())
        # Initiate plot and add it to the gui
        self.plot_settings = {'colors': ['b'], 'x_label': 'Points'}
        self.plot = NPointRunning(number_of_points=points,
                                  **self.plot_settings)
        hbox = self.gui('hbox1')
        hbox.pack_start(self.plot)
        hbox.reorder_child(self.plot, 0)

        # Initiate gui with value from device
        self.sync_gui_with_device()

        self.builder.connect_signals(self)

    ########## CONVINIENCE METHODS
    def gui(self, name):
        """ Convinience function to get GUI objects """
        return self.builder.get_object(name)

    def get_active_combo_element(self, widget):
        """ Convinience function to get the active element from a combobox """
        active = widget.get_active()
        model = widget.get_model()
        return model[active]

    ########## SIGNAL CALL BACKS
    def on_combobox_type_changed(self, widget):
        """ Method that handles changes in what is measured """
        # Get the active selection and change the state
        active = widget.get_active()
        model = widget.get_model()
        selection = self.get_active_combo_element(widget)[1]
        self.device.selectMeasurementFunction(selection)
        if selection == 'VOLTAGE':
            self.gui('combobox_internal_res').set_sensitive(True)
        else:
            self.gui('combobox_internal_res').set_sensitive(False)

    def on_combobox_internal_res_changed(self, widget):
        """ Signal call back settings the internal resistance for bias
        measurements
        """
        selection = self.get_active_combo_element(widget)[1]
        self.device.setAutoInputZ(selection)

    def on_combobox_integration_time_changed(self, widget):
        """ Signal call back for setting the integration time """
        selection = self.get_active_combo_element(widget)[1]
        # FIXME set in device
        print type(selection)
        print "Set integration time {0} NPLC".format(selection)

    def on_entry_format_changed(self, widget):
        number_format = widget.get_text()
        try:
            '{{0:{0}}}'.format(number_format).format(float())
            self.number_format = number_format
        except ValueError:
            pass

    def on_spinbutton_points_value_changed(self, widget):
        """ Method that handles changes in the number of points """
        points = int(self.gui('spinbutton_points').get_value())
        # Plot object is not thread safe, so we must pause updating ...
        if self.update_timer is not None:
            gobject.source_remove(self.update_timer)
            self.update_timer = None
        self.plot.__init__(number_of_points=points,
                           **self.plot_settings)
        self.win.show_all()
        # and start it back up
        self.set_update()

    def set_update(self, widget=None):
        """ Method to change the timing of the update. It is called both from
        'toggle_update' and 'spinbutton_interval'
        """
        updating_active = self.gui('toggle_update').get_active()
        if updating_active:
            if self.update_timer is not None:
                gobject.source_remove(self.update_timer)
            self.update_interval = int(self.gui('spinbutton_interval')\
                                           .get_value())
            self.update_timer = gobject.idle_add(self.update)
        elif not updating_active and self.update_timer is not None:
            gobject.source_remove(self.update_timer)
            self.update_timer = None

    def on_window_destroy(self, widget):
        """ Mandatory gui method to quit when the window is destroyed """
        gtk.main_quit()

    ########## GUI UPDATING METHODS
    def sync_gui_with_device(self):
        """ Synchronize the gui with values from the device."""
        # FIXME FIXME FIXME
        #  Disable signals while updating widgets
        #for items in self.__dict__:
        #    print items
        #print gobject.signal_lookup('on_change', gtk.ComboBox)
        #print gobject.signal_lookup('on_combobox_type_changed', gtk.ComboBox)
        type_ = 'VOLTAGE'# FIXME get type from device,
        type_model = self.gui('combobox_type').get_model()
        number = dict([[m[1], n] for n, m in enumerate(type_model)])[type_]
        self.gui('combobox_type').set_active(number)

    def update(self):
        """ Ask for measurement and update graph """
        start = time.time()
        measurement = self.device.read()
        measurement_string = '{{0:{0}}}'.\
            format(self.number_format).format(measurement)
        self.gui('label_measurement').set_text(measurement_string)
        self.plot.push_new_points([measurement])
        delta = time.time() - start
        if self.update_interval > 0:
            sleeptime = self.update_interval / 1000.0 - delta
            if sleeptime > 0:
                time.sleep(sleeptime)
            else:
                pass  # We can't keep up, consider warning
        return True

if __name__ == "__main__":
    MULTIMETER = Multimeter()
    MULTIMETER.win.show_all()
    gtk.main()

    #def on_RANGES(self, widget_name, options):
        #""" Change range REWRITE """
        # Get list store from buidler, set the model
        #combo.set_model(liststore)
        # Figure out if we can use the same renderer, otherwise, change it
        # and update
        #cell = gtk.CellRendererText()
        #combo.pack_start(cell, True)
        #combo.add_attribute(cell, "text", 0)
        #return combo
        #pass
