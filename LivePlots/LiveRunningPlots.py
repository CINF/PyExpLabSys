import matplotlib
matplotlib.use('GTKAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg

import gtk

import time

class Plot():
    pass

class NPointRunning(gtk.HBox):
    """ A N point running plot """
    def __init__(self, number_of_points=100, number_of_lines=1, dpi=100,
                 x_pixel_size=500, y_pixel_size=400, **kw):
        """ Init plot:
        Parameters:
            number_of_points (int)
            number_of_lines (int)
            dpi (int)
            x_pixel_size (int)
            y_pixel_size (int)
          **kw can contain:
            logscale (boolean)
            title (string)
            x_label (string)
            y_label (string)
            legends (list of strings)
            styles (list of strings)
        """
        gtk.HBox.__init__(self)
        fig = Figure(figsize=(x_pixel_size/100.1, y_pixel_size/100.0), dpi=dpi)
        fig.set_facecolor('white')
        self.canvas = FigureCanvasGTKAgg(fig)
        self.ax = fig.add_subplot(111)
        self.pack_start(self.canvas)

        # Assign settings to variable
        self.first_ever_update = True
        self.settings = {'logscale': False, 'title': None, 'x_label': None,
                         'y_label': None, 'legends': None, 'styles': None}
        self.change_settings(number_of_points, number_of_lines, **kw)

    def change_settings(self, number_of_points, number_of_lines, **kw):
        self.settings.update(kw)
        self.n_points = number_of_points
        self.n_lines = number_of_lines
        self.styles = kw['styles'] if kw.has_key('styles') else ['']*self.n_lines
        self.x = range(number_of_points)
        self.y = [[1]+[None]*(number_of_points-1)]*number_of_lines
        self.lines = None
        self.background = None
        self._reinit_plot()

    def _reinit_plot(self):
        plot = self.ax.semilogy if self.settings['logscale'] else self.ax.plot
        self.lines = [plot(self.x, y, style, animated=True)[0]
                      for y, style in zip(self.y, self.styles)]
        if self.settings['legends'] is not None:
            self.ax.legend(self.lines, self.settings['legends'], loc=2)
        self.ax.set_xlim(-1, self.n_points)
        self.ax.set_ylim(0.09, 1.11)
        self.canvas.draw()
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        [line.set_animated(False) for line in self.lines]
        self.canvas.draw() 
        [line.set_animated(True) for line in self.lines]

    def push_new_point(self, y):
        [y_data.append(new_y) for y_data, new_y in zip(self.y, y)]
        self.y = [y_data[self.n_points * -1:] for y_data in self.y]
        if self.first_ever_update:
            self._reinit_plot()
            self.first_ever_update = False

        self.canvas.restore_region(self.background)
        [line.set_ydata(y_data) for line, y_data in zip(self.lines, self.y)]
        [self.ax.draw_artist(line) for line in self.lines]
        # just redraw the axes rectangle
        self.canvas.blit(self.ax.bbox)

    def set_data(self, y):
        """ Not tested """
        if len(y) != self.n_lines:
            raise(Exception)
        for data in y:
            if len(data) != self.n_points:
                raise(Exception)

        [y_data.append(new_y) for y_data, new_y in zip(self.y, y)]
        self.y = [y_data[self.n_points * -1:] for y_data in self.y]
        if self.first_ever_update:
            self._reinit_plot()
            self.first_ever_update = False

        self.canvas.restore_region(self.background)
        [line.set_ydata(y_data) for line, y_data in zip(self.lines, self.y)]
        [self.ax.draw_artist(line) for line in self.lines]
        # just redraw the axes rectangle
        self.canvas.blit(self.ax.bbox)
