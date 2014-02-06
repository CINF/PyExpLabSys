""" Module that contains QT widgets for mass spectrometer channels and channel
lists
"""

from PyQt4 import QtGui, QtCore
from channel import Channel

class QtMSChannel(object):
    """ Mass spectrometer channel including separate widgets to change the
    values. These widgets are meant to be included separately in a grid.

    The widget defined are:
    active: A checkbox
    mass: A (??? float input)
    time: A (??? float input)
    delay:
    label:
    color: A colored button that activates a color selection dialog
    auto_label:
    """

    def __init__(self, parent, channel):
        """ Initialize the QtMSChannel """
        # Instantiate ???
        self._channel = channel
        # Initialize widgets
        self._gui = {'active': QtGui.QCheckBox('Active', parent)}

    def gui(self, name):
        """ Return the GUI component with the given name """
        return self._gui[name]
