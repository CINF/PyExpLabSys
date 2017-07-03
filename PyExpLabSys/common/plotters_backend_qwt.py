# pylint: disable=W0142,R0903,R0913

"""This module contains plotting backends that use the PyQwt library"""

from random import choice
import collections
import os

import numpy as np
try:
    from PyQt4 import Qt, QtGui, QtCore
    import PyQt4.Qwt5 as Qwt
except ImportError:
    # If we are building docs for read the docs, make fake version else re-raise
    import sys
    if os.environ.get('READTHEDOCS', None) == 'True' or 'sphinx' in sys.modules:
        class Qwt:
            QwtPlot = list
    else:
        raise

class Colors:
    """Class that gives plot colors"""
    def __init__(self):
        self.current = -1
        self.predefined = []
        self.colors = QtGui.QColor.colorNames()
        for name in ['blue', 'red', 'black', 'green', 'magenta']:
            index = self.colors.indexOf(QtCore.QString(name))
            self.predefined.append(self.colors[index])
            self.colors.removeAt(index)

    def get_color(self):
        """Return a color"""
        self.current += 1
        if self.current < len(self.predefined):
            return self.predefined[self.current]
        else:
            out = choice(self.colors)
            self.colors.removeAt(self.colors.indexOf(out))
            return out


class QwtPlot(Qwt.QwtPlot):
    """Class that represents a Qwt plot"""
    def __init__(self, parent, left_plotlist, right_plotlist=None,
                 left_log=False, right_log=False,
                 **kwargs):
        """Initialize the plot and local setting

        :param parent: The parent GUI object, then that should be supplied here
        :type parent: GUI object
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
        super(QwtPlot, self).__init__(parent)
        self.colors = Colors()
        self._curves = {}

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
        if message is not None:
            raise ValueError(message)

        # Set background color
        self._init_background(kwargs)
        # Form curves for the left axis
        self._init_left_curves(left_plotlist, kwargs)
        # Init the right axis and curves on it
        if right_plotlist is not None:
            self._init_right_curves(right_plotlist, kwargs)
        # Set log scales
        self._init_logscales(left_log, right_log, right_plotlist)
        # Title, xis labels and legends
        self._init_title_label_legend(right_plotlist, kwargs)

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

    def _init_background(self, kwargs):
        """Init the background color of the graph"""
        if kwargs.get('background_color') is not None:
            self.setCanvasBackground(
                QtGui.QColor(kwargs['background_color']))

    def _init_left_curves(self, left_plotlist, kwargs):
        """Init the curves on the left axis"""
        for index, plot in enumerate(left_plotlist):
            label = plot
            if kwargs.get('left_labels') is not None:
                label = kwargs['left_labels'][index]
            curve = Qwt.QwtPlotCurve(label)

            if kwargs.get('left_colors') is not None:
                color = kwargs['left_colors'][index]
            else:
                color = self.colors.get_color()

            if kwargs.get('left_thickness') is not None:
                if isinstance(kwargs['left_thickness'], collections.Iterable):
                    thickness = kwargs['left_thickness'][index]
                else:
                    thickness = kwargs['left_thickness']
                curve.setPen(Qt.QPen(QtGui.QColor(color), thickness))
            else:
                curve.setPen(Qt.QPen(QtGui.QColor(color)))

            curve.attach(self)
            self._curves[plot] = curve

    def _init_right_curves(self, right_plotlist, kwargs):
        """Init the right y axis and the curves on it"""
        self.enableAxis(QwtPlot.yRight)

        # Form the right axis curves
        for index, plot in enumerate(right_plotlist):
            label = plot
            if kwargs.get('right_labels') is not None:
                label = kwargs['right_labels'][index]
            curve = Qwt.QwtPlotCurve(label)
            curve.setYAxis(QwtPlot.yRight)

            if kwargs.get('right_colors') is not None:
                color = kwargs['right_colors'][index]
            else:
                color = self.colors.get_color()
            curve.setPen(Qt.QPen(QtGui.QColor(color)))

            if kwargs.get('right_thickness') is not None:
                if isinstance(kwargs['right_thickness'], collections.Iterable):
                    thickness = kwargs['right_thickness'][index]
                else:
                    thickness = kwargs['right_thickness']
                curve.setPen(Qt.QPen(QtGui.QColor(color), thickness))
            else:
                curve.setPen(Qt.QPen(QtGui.QColor(color)))

            curve.attach(self)
            self._curves[plot] = curve

    def _init_logscales(self, left_log, right_log, right_plotlist):
        """Init log scales"""
        if left_log:
            self.setAxisScaleEngine(QwtPlot.yLeft, Qwt.QwtLog10ScaleEngine())
        if right_log and (right_plotlist is not None):
            self.setAxisScaleEngine(QwtPlot.yRight, Qwt.QwtLog10ScaleEngine())

    def _init_title_label_legend(self, right_plotlist, kwargs):
        """Init the title, axis labels and legends"""
        if kwargs.get('legend') is not None:
            legend_name = kwargs['legend'].title() + 'Legend'
            self.insertLegend(Qwt.QwtLegend(),
                              getattr(Qwt.QwtPlot, legend_name))
        if kwargs.get('title') is not None:
            self.setTitle(kwargs['title'])
        if kwargs.get('xaxis_label') is not None:
            self.setAxisTitle(Qwt.QwtPlot.xBottom, kwargs['xaxis_label'])
        if kwargs.get('yaxis_left_label') is not None:
            self.setAxisTitle(Qwt.QwtPlot.yLeft,
                              kwargs['yaxis_left_label'])
        if kwargs.get('yaxis_right_label') is not None and \
                right_plotlist is not None:
            self.setAxisTitle(Qwt.QwtPlot.yRight,
                              kwargs['yaxis_right_label'])

    def update(self, data):
        """Update the plot with new values and possibly move the xaxis
        
        :param data: The data to plot. Should be a dict, where keys are plot
            code names and values are data series as an iterable of (x, y)
            iterables. E.g. {'plot1': [(1, 1), (2, 2)]}
        :type data: dict
        """
        for key, dataseries in data.items():
            if len(dataseries) > 0:
                values_array = np.array(dataseries)
                self._curves[key].setData(values_array[:, 0],
                                          values_array[:, 1])
        self.replot()
