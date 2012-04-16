# -*- coding: utf-8 -*-

""" Base class for the plots """
import gtk
import matplotlib
matplotlib.use('GTKAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg
import matplotlib.transforms as mtransforms
import random

class Plot(gtk.HBox):
    """ Base class for LivePlots. This class is an abstract class. In addition
    to inheriting from this class it is also required to take the following
    actions to achieve a functioning plot:
    Bla bla bla
    """
    
    def __init__(self, dpi=100, x_pixel_size=500, y_pixel_size=400):
        gtk.HBox.__init__(self)
        # If the class is being reinitialized, we need to remove the old plot
        [self.remove(child) for child in self.get_children()]
        self.vbox = gtk.VBox()
        self.pack_start(self.vbox)
        # this is bad with labels, I have to figure out why
        self.connect('size_allocate', self._full_update)

        self.fig = Figure(figsize=(x_pixel_size/100.1, y_pixel_size/100.0), dpi=dpi)
        self.fig.set_facecolor('white')
        self.canvas = FigureCanvasGTKAgg(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.vbox.pack_end(self.canvas)
        self.canvas.connect('button_press_event', self._on_mouse_click)

        self.first_update = True
        self.settings = {}
        self.n_lines = None
        #self.line_styles = None
        #self.line_colors = None
        self.lines = None
        self.saved_window_size = None
        self.background = None
        self.auto_x_scale = False
        self.auto_y_scale = False

    def _change_settings_common(self, number_of_lines, **kw):
        """ Change the subset of settings that are common for all plots """
        self.settings.update(kw)
        self.n_lines = number_of_lines
        self.line_styles = kw['line_styles'] if kw.has_key('line_styles')\
            else ['']*self.n_lines
        self.line_colors = kw['line_colors'] if kw.has_key('line_colors')\
            else self._get_colors(self.n_lines)
        self.lines = None
        self.background = None

        if self.settings['legends'] is not None:
            c = matplotlib.colors.ColorConverter()
            colors = [matplotlib.colors.rgb2hex(c.to_rgb(color))
                      for color in self.line_colors]
            self.legends = Legends(self.settings['legends'],
                                   colors,
                                   self.settings['legend_placement'],
                                   self.settings['legend_cols'])
            if self.settings['legend_placement'] == 'top':
                self.vbox.pack_end(self.legends, expand=False)
            else:
                self.pack_end(self.legends, expand=False)


    def _on_mouse_click(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            b1 = gtk.MenuItem("A button")
            b2 = gtk.MenuItem("Another")
            menu = gtk.Menu()
            menu.append(b1)
            menu.append(b2)
            b1.show()
            b2.show()
            menu.popup(None, None, None, event.button, event.time)

    def _update_bounds(self):
        return self._update_x_bounds() or self._update_y_bounds()

    def _update_x_bounds(self):
        if not self.auto_x_scale:
            return False

    def _update_y_bounds(self):
        modified = False
        if not self.auto_y_scale:
            return modified

        # Combine data (double loop), sort out None and get min/max
        y_min = min([inner for outer in self.y for inner in outer\
                         if inner is not None])
        y_max = max([inner for outer in self.y for inner in outer\
                         if inner is not None])
        delta = y_max - y_min
        if delta < 1E-10:
            return modified

        br = 0.2
        if y_min < self.settings['y_bounds'][0]:
            self.settings['y_bounds'] =\
                (y_min-br*delta, self.settings['y_bounds'][1])
            modified = True
        elif y_min > self.settings['y_bounds'][0] + br*delta:
            self.settings['y_bounds'] =\
                (y_min, self.settings['y_bounds'][1])
            modified = True

        if y_max > self.settings['y_bounds'][1]:
            self.settings['y_bounds'] =\
                (self.settings['y_bounds'][0], y_max+br*delta)
            modified = True
        elif y_max < self.settings['y_bounds'][1] - br*delta:
            self.settings['y_bounds'] =\
                (self.settings['y_bounds'][0], y_max)
            modified = True

        return modified

    def update_legends(self):
        if self.settings['legends'] is not None:
            for n in range(self.n_lines):
                point = self.y[n][-1]
                self.legends.set_legend_text(n, point)

    def _quick_update(self):
        if self.first_update:
            self._full_update()
            self.first_update = False
        self.canvas.restore_region(self.background)
        [line.set_ydata(y_data) for line, y_data in zip(self.lines, self.y)]
        [self.ax.draw_artist(line) for line in self.lines]
        # just redraw the axes rectangle
        self.canvas.blit(self.ax.bbox)

    def _full_update(self, widget=None, size=None):
        # This does not work properly, FIXME
        if widget is not None:
            if [size.width, size.height] != self.saved_window_size:
                self.saved_window_size = [size.width, size.height]
            else:
                return
        # Plot
        if self.first_update:
            plot = self.ax.semilogy if self.settings['logscale'] else self.ax.plot
            self.lines = [plot(x, y, style, color=color, animated=True)[0]
                          for x, y, color, style in
                          zip(self.x, self.y, self.line_colors, self.line_styles)]
            # Title and axis labels
            if self.settings['title'] is not None:
                self.ax.set_title(self.settings['title'])
            if self.settings['x_label'] is not None:
                self.ax.set_xlabel(self.settings['x_label'])
            if self.settings['y_label'] is not None:
                self.ax.set_ylabel(self.settings['y_label'])
            self.fig.subplots_adjust(left=0.25, bottom=0.15)
        else:
            [line.set_ydata(y_data) for line, y_data in zip(self.lines, self.y)]

        # Get or set boundaries
        if self.first_update:
            if self.settings['x_bounds'] is None:
                self.settings['x_bounds'] = self.ax.get_xlim()
            if self.settings['y_bounds'] is None:
                self.settings['y_bounds'] = self.ax.get_ylim()
        else:
            self.ax.set_xlim(*self.settings['x_bounds'])
            self.ax.set_ylim(*self.settings['y_bounds'])

        # Get the background for later use
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        # First draw update
        [line.set_animated(False) for line in self.lines]
        self.canvas.draw()
        [line.set_animated(True) for line in self.lines]

    def _get_colors(self, n):
        """ Generate colors for the lines if they are not provided. First use
        6 of the standard colors and then generate random colors

        Parameters:
            n -- the number of colors requested
        """
        standard = ['r', 'g', 'b', 'c', 'm', 'k']
        if n <= len(standard):
            out = standard[:n]
        else:
            out = standard
        if n > len(standard):
            for i in range(len(standard), n):
                out.append((random.random(), random.random(), random.random()))
        return out
            
class Legends(gtk.HBox):
    """ This class forms a gui element with all the legends and provides a
    convinience method for updating the legends with current measurements
    """

    def __init__(self, legends, line_colors, placement, number_of_columns=1,
                 legend_width_right=150):
        # We lay out a mesh of the HBox we inherit from and VBoxes
        gtk.HBox.__init__(self)
        columns = [gtk.VBox() for n in range(number_of_columns)]
        [self.pack_start(vbox) for vbox in columns]
        # Initialize variables
        color = gtk.gdk.color_parse('#ffffff')
        self.legends = legends
        self.line_colors = line_colors
        self.labels = []; self.event_boxes = []
        # Create the label elements for the legends
        for legend in legends:
            self.labels.append(gtk.Label(legend))
            self.labels[-1].set_alignment(0, 0.5)
            if placement == 'right':
                self.labels[-1].set_size_request(legend_width_right, -1)
            # We put the labels in eventboxes to be able to color them
            eb = gtk.EventBox()
            eb.modify_bg(gtk.STATE_NORMAL, color)
            eb.add(self.labels[-1])
            self.event_boxes.append(eb)

        # Put the labels (in eventboxes) in the mesh
        [columns[n % number_of_columns].pack_start(ebox, expand=False)
         for n, ebox in enumerate(self.event_boxes)]

        # Fill in white labels in the missing spaces
        if placement == 'top':
            for col in columns:
                if len(col.get_children()) < len(columns[0].get_children()):
                    eb = gtk.EventBox()
                    eb.modify_bg(gtk.STATE_NORMAL, color)
                    eb.add(gtk.Label())
                    col.pack_start(eb, expand=False)
        else:
            for col in columns:
                eb = gtk.EventBox()
                eb.modify_bg(gtk.STATE_NORMAL, color)
                eb.add(gtk.Label())
                col.pack_start(eb, expand=True)

    def set_legend_text(self, number, point):
        text = '<span foreground="{{2}}" >●</span> {{0}}: {{1:{0}}}'.\
            format('.2e').format(self.legends[number], point, self.line_colors[number])
        self.labels[number].set_text(text)
        self.labels[number].set_use_markup(True)
