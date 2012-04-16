
""" Running Plots """

#import matplotlib
#matplotlib.use('GTKAgg')
#from matplotlib.figure import Figure
#from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg

from LivePlotsCommon import Plot
from LivePlotsExceptions import NLinesError, NDataError

import gtk
import time

class NPointRunning(Plot):
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
            line_styles (list of strings)
            colors (list of strings)
            y_bounds (list of floats) -- [y_min, y_max] if not given->autoscale
            legends (list of strings)
            legend_cols (integer)
            legend_placement (string) -- right (default) or top
            legend_width_right (integer)
            number_in_legend (boolean) -- True (default)
            legend_number_format (string) -- .2f (default)
        """
        Plot.__init__(self, dpi, x_pixel_size, y_pixel_size)

        # Assign settings to variable
        if not kw.has_key('y_bounds'):
            self.auto_y_scale = True
        self.auto_x_scale = False
        # These work as defaults
        self.settings = {'logscale': False,
                         'title': None,
                         'x_label': None,
                         'y_label': None,
                         'line_styles': None,
                         'line_colors': None,
                         'y_bounds': None,
                         'x_bounds': (-1, number_of_points),
                         'y_bounds': None,
                         'legends': None,
                         'legend_cols': 1,
                         'legend_placement': 'right',
                         'legend_width_right': 100,
                         'number_in_legend': True,
                         'legend_number_format': '.2f'}
        # Update common settings (iniherited from LivePlotsCommon)
        self._change_settings_common(number_of_lines, **kw)
        # Update settings specific to this type of plot and init the data
        self.n_points = number_of_points
        self.x = [range(number_of_points)]
        [self.x.append(self.x[0]) for n in range(1, number_of_lines)]
        self.y = [[1]+[None]*(number_of_points-1)]*number_of_lines

        self._full_update()

    def push_new_points(self, points):
        """ Push new points to the lines 

        Attributes:
            points -- list of new points, one item in the list per line, must 
                      be a list even with just one line, the data point for a
                      line can be None
        """
        if not isinstance(points, list):
            raise TypeError('This function must be passed a list')
        if len(points) != self.n_lines:
            raise NLinesError(len(points), self.n_lines)

        [y_data.append(new_y) for y_data, new_y in zip(self.y, points)]
        self.y = [y_data[self.n_points * -1:] for y_data in self.y]
        if self._update_bounds():
            self._full_update()
        self._quick_update()
        self.update_legends()

    def set_data(self, data):
        """ Replace the entire data set

        Attributes:
            data -- list of lists of points, must contain one list per line
                    that each contains as many points as the plot does
        """
        if not isinstance(data, list):
            raise TypeError('This function must be passed a list')
        if len(data) != self.n_lines:
            raise NLinesError(len(y), self.n_points)
        for points in data:
            if len(data) != self.n_points:
                raise NDataError(len(data), self.n_points)

        self.y = data
        self._quick_update()
        self.update_legends()

    def set_number_of_points(self, n_points):
        self.x[0] = range(n_points)
        if n_points > self.n_points:
            self.y = [[None] * (n_points - self.n_points) + y for y in self.y]
        else:
            self.y = [y[n_points * -1:] for y in self.y]
        print len(self.x)
        print len(self.x[0])
        print len(self.y)
        print len(self.y[0])
        self.n_points = n_points
        self.settings['x_bounds'] = (-1, n_points)
        self.first_update = True
        self._quick_update()
