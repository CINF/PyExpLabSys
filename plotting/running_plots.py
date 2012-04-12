import matplotlib
matplotlib.use('GTKAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg

import time

class NPointRunning(FigureCanvasGTKAgg):
    """ A N point running plot """

    def __init__(self, number_of_points, number_of_lines, x_pixel_size=500, y_pixel_size=400, **kw):
        """ Init plot:
        
        Parameters:
            number_of_points (int)
            number_of_lines (int)
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
        # Assign settings to variable
        self.settings = {'logscale': False, 'title': None, 'x_label': None,
                         'y_label': None, 'legends': None, 'styles': None}
        self.change_settings(number_of_points, number_of_lines, init=True, **kw)
        
        self.first_ever_update = True

        fig = Figure(figsize=(x_pixel_size/100.1, y_pixel_size/100.0), dpi=100)
        fig.set_facecolor('white')
        FigureCanvasGTKAgg.__init__(self, fig)
        self.ax = fig.add_subplot(111)

        self._reinit_plot()

    def change_settings(self, number_of_points, number_of_lines, init=False, **kw):
        self.settings.update(kw)
        self.n_points = number_of_points
        self.n_lines = number_of_lines
        self.styles = kw['styles'] if kw.has_key('styles') else ['']*self.n_lines
        self.x = range(number_of_points)
        self.y = [[1]+[None]*(number_of_points-1)]*number_of_lines
        self.lines = None
        self.background = None
        if not init:
            self._reinit_plot()

    def _reinit_plot(self):
        plot = self.ax.semilogy if self.settings['logscale'] else self.ax.plot
        self.lines = [plot(self.x, y, style, animated=True)[0]
                      for y, style in zip(self.y, self.styles)]
        if self.settings['legends'] is not None:
            self.ax.legend(self.lines, self.settings['legends'], loc=2)
        self.ax.set_xlim(-1, self.n_points)
        self.ax.set_ylim(0.09, 1.11)
        self.draw()
        self.background = self.copy_from_bbox(self.ax.bbox)
        [line.set_animated(False) for line in self.lines]
        self.draw() 
        [line.set_animated(True) for line in self.lines]

    def push_new_point(self, y):
        [y_data.append(new_y) for y_data, new_y in zip(self.y, y)]
        self.y = [y_data[self.n_points * -1:] for y_data in self.y]
        if self.first_ever_update:
            self._reinit_plot()
            self.first_ever_update = False

        self.restore_region(self.background)
        [line.set_ydata(y_data) for line, y_data in zip(self.lines, self.y)]
        [self.ax.draw_artist(line) for line in self.lines]
        # just redraw the axes rectangle
        self.blit(self.ax.bbox)
