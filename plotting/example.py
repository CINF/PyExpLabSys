#!/usr/bin/env python 

import gtk 
import gobject 
import numpy as np 

from matplotlib.figure import Figure 
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas 
from matplotlib.backends.backend_gtk import NavigationToolbar2GTK as NavigationToolbar 

## 
# Simple GTK windows base classes 
# 
class BaseWindow: 
    """A base gtk window that can be closed.""" 
    def __init__(self): 
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL) 
        self.window.set_default_size(550, 500) 
        self.window.connect("delete_event", self.on_delete_event) 
        self.window.connect("destroy", self.on_destroy) 
    def main(self): 
        gtk.main() 
    def on_delete_event(self, widget, *args): 
        return False 
    def on_destroy(self, widget, data=None): 
        gtk.main_quit() 

class PlotWindow(BaseWindow): 
    """A gtk window with a figure inside.""" 
    def __init__(self, show=True, create_axis=False): 
        BaseWindow.__init__(self) 
        self.figure = Figure() 
        self.canvas = FigureCanvas(self.figure) 
        if create_axis: self.ax = self.figure.add_subplot(111) 
        self.toolbar = NavigationToolbar(self.canvas, self.window) 
        self.vbox = gtk.VBox() 
        self.vbox.pack_start(self.toolbar, expand=False) 
        self.vbox.pack_start(self.canvas, expand=True) 
        self.window.add(self.vbox) 
        if show: self.window.show_all() 

## 
# The main application 
# 
class Plotter(PlotWindow): 
    def __init__(self): 
        PlotWindow.__init__(self, create_axis=True, show=False) 
        
        # Add two buttons to the toolbar: scale and play 
        self.scalebutton = gtk.ToolButton(gtk.STOCK_ZOOM_FIT) 
        self.scalebutton.connect("clicked", self.scale_clicked) 
        self.toolbar.insert(self.scalebutton, 0) 
        self.playbutton = gtk.ToggleToolButton(gtk.STOCK_MEDIA_PLAY) 
        self.playbutton.set_active(False) 
        self.playbutton.connect("clicked", self.play_toggled) 
        self.toolbar.insert(self.playbutton, 0) 
        self.window.show_all() 

        # Create the plot, the first frame (note that animated=True) 
        self.t = np.arange(100)*0.1 
        self.line, = self.ax.plot(self.t, np.sin(self.t), animated=True) 
        self.ax.grid(True) 
        
        # Finalize the plot 
        self.refresh() 

        self.n = 0 
        self.main() # Start the gtk main loop 

    def refresh_wrong(self): 
        self.line.set_animated(False) 
        self.canvas.draw() 
        self.line.set_animated(True) 
        self.background = self.canvas.copy_from_bbox(self.ax.bbox) 
        
    def refresh(self): 
        # This explicit draw is needed to draw the grid and to save a clean 
        # background 
        self.canvas.draw() 
        self.background = self.canvas.copy_from_bbox(self.ax.bbox) 
        
        # This draw is needed to draw the stand-still plot (first frame) 
        self.line.set_animated(False) 
        self.canvas.draw() 
        self.line.set_animated(True) 
            # NOTE: Saving the background here would save the line too 

    def play_toggled(self, widget): 
        if self.playbutton.get_active(): 
            self.gid = gobject.timeout_add(50, self.update_fast) 
        else: 
            gobject.source_remove(self.gid) 

    def scale_clicked(self, widget): 
        x, y = self.line.get_xdata(), self.line.get_ydata() 
        self.ax.set_ylim([y.min()*2, y.max()*2]) 
        self.ax.set_xlim([x.min()-2, x.max()+2]) 
        self.refresh() 

    def update_slow(self): 
        """This is the classic update, not suitable for animations.""" 
        self.n += 1 
        self.line.set_ydata(np.sin(self.t+self.n*0.1)) 
        self.canvas.draw() 
        return True 

    def update_fast(self): 
        """The fast (blit) update to be used in animations.""" 
        self.n += 1 
        # restore the clean slate background 
        self.canvas.restore_region(self.background) 
        # update the data 
        self.line.set_ydata(np.sin(self.t+self.n*0.1)) 
        # just draw the animated artist 
        self.ax.draw_artist(self.line) 
        # just redraw the axes rectangle 
        self.canvas.blit(self.ax.bbox) 
        return True 


if __name__ == "__main__": 
    Plotter() 
