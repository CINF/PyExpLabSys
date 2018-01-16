# pylint: disable=R0913,R0912

"""This module contains plotters for experimental data gathering applications.
It contains a plotter for data sets.
"""

import time
import collections
import numpy


class DataPlotter(object):
    """This class provides a data plotter for continuous data"""

    def __init__(self, left_plotlist, right_plotlist=None, left_log=False,
                 right_log=False, auto_update=True, backend='qwt', parent=None,
                 **kwargs):
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
        :param auto_update: Whether all data actions should trigger an update
        :type auto_update: bool
        :param backend: The plotting backend to use. Current only option is
            'qwt'
        :type backend: str
        :param parent: If a GUI backend is used that needs to know the parent
            GUI object, then that should be supplied here
        :type parent: GUI object

        Kwargs:

        :param title: The title of the plot
        :type title: str
        :param xaxis_label: Label for the x axis
        :type xaxis_label: str
        :param yaxis_left_label: Label for the left y axis
        :type yaxis_left_label: str
        :param yaxis_right_label: Label for the right y axis
        :type yaxis_right_label: str
        :param left_labels: Labels for the plots on the left y-axis. If none
            are given the codenames will be used.
        :type left_labels: iterable with strs
        :param right_labels: Labels for the plots on the right y-axis. If none
            are given the codenames will be used.
        :type right_labels: iterable with strs
        :param legend: Position of the legend. Possible values are:
            'left', 'right', 'bottom', 'top'. If no argument is given, the
            legend will not be shown.
        :type legend: str
        :param left_colors: Colors for the left curves (see background_color
            for details)
        :type left_colors: iterable of strs
        :param right_colors: Colors for the right curves (see background_color
            for details)
        :type right_colors: iterable of strs
        :param left_thickness: Line thickness. Either an integer to apply for
            all left lines or a iterable of integers, one for each line.
        :type left_thickness: int or iterable of ints
        :param right_thickness: Line thickness. Either an integer to apply for
            all right lines or a iterable of integers, one for each line.
        :type right_thickness: int or iterable of ints
        :param background_color: The name in a str (as understood by
            QtGui.QColor(), see :ref:`colors-section` section for possible
            values) or a string with a hex value e.g. '#101010' that should
            be used as the background color.
        :type background_color: str
        """
        # Gather all plots
        all_plots = list(left_plotlist)
        if right_plotlist is not None:
            all_plots += list(right_plotlist)

        # Input checks
        message = self._init_check_left(left_plotlist, kwargs)
        # Check number of right labels, colors and thickness
        message = message or self._init_check_right(right_plotlist, kwargs)
        # Check legend
        message = message or self._init_check_legends_plots(all_plots, kwargs)
        # Backend
        if backend not in ['qwt']:
            message = 'Backend must be \'qwt\''
        if message is not None:
            raise ValueError(message)

        # Initiate the backend
        if backend == 'qwt':
            from PyExpLabSys.common.plotters_backend_qwt import QwtPlot
            self._plot = QwtPlot(parent, left_plotlist, right_plotlist,
                                 left_log, right_log,
                                 **kwargs)

        # Initiate the data
        self._data = {}
        for plot in all_plots:
            self._data[plot] = []

        self.auto_update = auto_update

    @staticmethod
    def _init_check_left(left_plotlist, kwargs):
        """Check input related to the left curves"""
        message = None
        if not len(left_plotlist) > 0:
            message = 'At least one item in left_plotlist is required'
        # Check number of left labels and colors
        for kwarg in ['left_labels', 'left_colors']:
            if kwargs.get(kwarg) is not None and\
                    len(left_plotlist) != len(kwargs.get(kwarg)):
                message = 'There must be as many items in \'{}\' as there '\
                    'are left plots'.format(kwarg)
        # Check left thickness if it is a list
        if kwargs.get('left_thickness') is not None and\
                isinstance(kwargs['left_thickness'], collections.Iterable) and\
                len(left_plotlist) != len(kwargs['left_thickness']):
            message = '\'left_thickness\' must either be an int or a iterable'\
                ' with as many ints as there are left plots'
        return message

    @staticmethod
    def _init_check_right(right_plotlist, kwargs):
        """Check input related to the right curves"""
        message = None
        if right_plotlist is not None:
            for kwarg in ['right_labels', 'right_colors']:
                if kwargs.get(kwarg) is not None and\
                        len(right_plotlist) != len(kwargs.get(kwarg)):
                    message = 'There must be as many items in \'{}\' as '\
                        'there are right plots'.format(kwarg)
            if kwargs.get('right_thickness') is not None and\
                isinstance(kwargs['right_thickness'], collections.Iterable)\
                    and len(right_plotlist) != len(kwargs['right_thickness']):
                message = '\'right_thickness\' must either be an int or a'\
                          ' iterable with as many ints as there are left plots'
        return message

    @staticmethod
    def _init_check_legends_plots(all_plots, kwargs):
        """Check legend name and for duplicate plot names"""
        message = None
        if kwargs.get('legend') is not None and not kwargs['legend'] in\
                ['left', 'right', 'bottom', 'top']:
            message = 'legend must be one of: \'left\', \'right\', '\
                '\'bottom\', \'top\''
        # Check for duplicate plot names
        for plot in all_plots:
            if all_plots.count(plot) > 1:
                message = 'Duplicate codename {} not allowed'.format(plot)
        return message

    def add_point(self, plot, point, update=None):
        """Add a point to a plot

        :param plot: The codename for the plot
        :type plot: str
        :param point: The point to add
        :type point: Iterable with x and y value as two numpy.float
        :param update: Whether a update should be performed after adding the
            point. If set, this value will over write the ``auto_update`` value
        :return: plot content or None
        """
        self._data[plot].append((numpy.float(point[0]), numpy.float(point[1])))
        if update or (update is None and self.auto_update):
            self.update()

    def update(self):
        """Update the plot and possible return the content"""
        self._plot.update(self._data)

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


class ContinuousPlotter(object):
    """This class provides a data plotter for continuous data"""

    def __init__(self, left_plotlist, right_plotlist=None, left_log=False,
                 right_log=False, timespan=600, preload=60, auto_update=True,
                 backend='none', **kwargs):
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
            'none'
        :type backend: str

        Kwargs

        TODO

        """
        # Gather all plots
        all_plots = list(left_plotlist)
        if right_plotlist is not None:
            all_plots += list(right_plotlist)

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
        if backend not in ['none']:
            message = 'Backend must be \'none\''
        for plot in all_plots:
            if all_plots.count(plot) > 1:
                message = 'Duplicate codename {} not allowed'.format(plot)
        if message is not None:
            raise ValueError(message)

        # Initiate the backend
        self._plot = None
        print(right_log, left_log)
        # TODO

        # Initiate the data
        self._data = {}
        for plot in all_plots:
            self._data[plot] = []

        self.timespan = timespan
        self.preload = preload
        self.auto_update = auto_update

        self.start = time.time()
        self.end = self.start + timespan

        message = 'No plotter for continuous data implemented'
        raise NotImplementedError(message)

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
        if now > self.end:
            self._reduce(now)
        self._plot.update(self._data, (self.start, self.end))

    def _reduce(self, now):
        """Update the plotting window and reduce the data accordingly"""
        self.end = now + self.preload
        self.start = self.end - self.timespan
        for plot, dataseries in self._data.items():
            for index, point in enumerate(dataseries):
                if point[0] > self.start:
                    self._data[plot] = dataseries[index:]
                    break

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
