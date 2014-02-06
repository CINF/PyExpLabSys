# pylint: disable=R0913

"""This module contains plotters for experimental data gathering applications.
It contains a plotter for continuous data and for data sets.
"""

import time
import numpy


class ContinuousPlotter(object):
    """This class provides a data plotter for continuous data"""

    def __init__(self, left_plotlist, right_plotlist=None, left_log=False,
                 right_log=False, timespan=600, preload=60, auto_update=True,
                 backend='qwt', **kwargs):
        """Initialize the plotting backend, data and local setting

        :param left_plotlist: Codenames for the plots that should go on the
            left y-axis
        :type left_plotlist: iterable with strs
        :param right_plotlist: Codenames for the plots that should go in the
            right y-axis
        :type left_plotlist: iterable with strs
        :param left_log: Left y-axis should be log
        :type left_log: bool
        :param right_log: Right y-axis should be log
        :type right_log: bool
        :param timespan: Numbers of seconds to show in the plot
        :type timespan: int
        :param preload: Number of seconds to jump ahead when reaching edge of
            plot
        :type preload: int
        :param auto_update: Whether all data actions should trigger a update
        :type auto_update: bool
        :param backend: The plotting backend to use. Current only option is
            'qwt'
        :type backend: str

        Kwargs

        :param left_labels: Labels for the plots on the left y-axis. If none
            are given the codenames will be used.
        :type left_labels: iterable with strs
        :param right_labels: Labels for the plots on the right y-axis. If none
            are given the codenames will be used.
        :type right_labels: iterable with strs
        :param title: The title of the plot
        :type title: str
        """
        # Gather all plots
        all_plots = left_plotlist
        if right_plotlist is not None:
            all_plots += right_plotlist

        # Input checks
        message = None
        if not len(left_plotlist) > 0:
            message = 'At least one item in left_plotlist is required'
        if kwargs.get('left_labels') is not None and\
                len(left_plotlist) != len(kwargs.get('left_labels')):
            message = 'There must be as many left labels as there are plots'
        if right_plotlist is not None and\
                kwargs.get('right_labels') is not None and\
                len(right_plotlist) != len(kwargs.get('right_labels')):
            message = 'There must be as many right labels as there are plots'
        if timespan < 1:
            message = 'timespan must be positive'
        if preload < 0:
            message = 'preload must be positive or 0'
        if backend not in ['qwt']:
            message = 'Backend must be \'qwt\''
        for plot in all_plots:
            if all_plots.count(plot) > 1:
                message = 'Duplicate codename {} not allowed'.format(plot)
        if message is not None:
            raise ValueError(message)

        # Initiate the backend
        if backend == 'qwt':
            self._plot = StandAloneQwtPlot(left_plotlist, right_plotlist,
                                           left_log, right_log, **kwargs)

        # Initiate the data
        self._data = {}
        for plot in all_plots:
            self._data[plot] = []

        self.timespan = timespan
        self.preload = preload
        self.auto_update = auto_update

    def add_point_now(self, plot, value, update=None):
        """Add a point to a plot using now as the time

        :param plot: The codename for the plot
        :type plot: str
        :param value: The value to add
        :type value: numpy.float
        :param update: Whether a update should be performed after adding the
            point. If set, this value will over write the ``auto_update`` value
        :return: plot content or None
        """
        self.add_point(plot, (time.time(), value), update)

    def add_point(self, plot, point, update=None):
        """Add a point to a plot

        :param plot: The codename for the plot
        :type plot: str
        :param point: The point to add
        :type point: Iterable with unix time and value as two numpy.float
        :param update: Whether a update should be performed after adding the
            point. If set, this value will over write the ``auto_update`` value
        :return: plot content or None
        """
        self._data[plot].append((numpy.float(point[0]), numpy.float(point[1])))
        if update or (update is None and self.auto_update):
            self.update()

    def update(self):
        """Update the plot and possible return the content"""
        now = time.time()
        for plot in self._data.keys():
            start = 0
            for point in self._date[plot]:
                if point[0] > 

    @property
    def data(self):
        """Get and set the data"""
        return self._data

    @data.setter
    def data(self, data):  # pylint: disable=C0111
        self._data = data

    @property
    def plot(self):
        """Get the plot"""
        return self._plot


class DataPlotter(object):
    """Plotter for data sets"""
    pass


class StandAloneQwtPlot(object):
    """Class for a stand alone Qwt plot"""

    def __init__(self, left_plotlist, right_plotlist, left_log, right_log,
                 dateplot=False, **kwargs):
        self.left_plotlist = left_plotlist
        self.right_plotlist = right_plotlist
        self.left_log = left_log
        self.right_log = right_log
        self.dateplot = dateplot
        self.kwargs = kwargs

    def update(self, data):
        """Update the plot"""
        pass
