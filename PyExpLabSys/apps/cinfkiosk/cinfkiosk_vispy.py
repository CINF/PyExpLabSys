
import time
import logging
logging.basicConfig(level=logging.DEBUG)
import xml.etree.ElementTree as ET

import numpy as np

import sys
if True:
    from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QGridLayout
    from PyQt5.QtWidgets import QSpacerItem
    from PyQt5.QtCore import QTimer
else:
    pass

import vispy
vispy.use(app='PyQT5')
from vispy.plot import Fig


def typed(xml):
    """Convert XML value to Python types"""
    type_ = xml.attrib['type']
    # The type function may be within brackets
    type_func = getattr(__builtins__, type_.strip('[]'))
    if type_.startswith('['):
        return [type_func(value.strip()) for value in xml.text.split(',')]
    else:
        return type_func(xml.text.strip())

clog = logging.getLogger('CinfFigure')
class CinfFigure(object):
    """Custom Vispy figure with a little data handling"""

    def __init__(self, xmlconf):
        self.xmlconf = xmlconf
        size = typed(xmlconf.find('size'))
        fig = Fig(size=size, show=False)
        print(fig.title)
        self.axes = fig[0, 0]  # PlotWidget
        # All line settings should go in the plot call:
        # http://vispy.org/plot.html#vispy.plot.PlotWidget.plot
        x = np.linspace(0, 6.28, 100)
        y1 = np.sin(x + time.time())
        y2 = np.random.random(100)
        self.lines1 = self.axes.plot((x, y1), ylabel="Pressure [mbar]", xlabel="Time") 
        self.lines2 = self.axes.plot((x, y2)) 
        self.native = fig.native
        fig.show()

    def update(self):
        """Update the figure"""
        x = np.linspace(0, 6.28, 100)
        y1 = np.sin(x + time.time())
        self.lines1.set_data((x, y1))
        self.lines1.update()


klog = logging.getLogger('kiosk')
class CinfKiosk(QWidget):
    """Cinf Kiosk main app"""
    
    def __init__(self, settings_file, screen_geometry):
        """Init local variables"""
        klog.debug('Init')
        super().__init__()
        self.xml = ET.parse(settings_file).getroot()
        self.screen_geometry = screen_geometry
        self.figures = {}
        self.init_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.setInterval(100)
        self.timer.start()
        
        
    def init_ui(self):
        """Init the UI"""
        klog.debug('init_ui')
        self.setWindowTitle('Cinfkiosk')
        #self.setWindowIcon(QIcon('web.png'))

        layout = QGridLayout(self)
        
        # Add graphs
        # FIXME Maybe flowlayout, gridlayout or anchorlayout
        max_column = 0
        max_row = 0
        for figure_def in self.xml.findall('figure'):
            # Make the figure
            figure_id = figure_def.attrib['id']
            if figure_id in self.figures:
                raise ValueError('The graph id must be unique. "{} already known"'.format(figure_id))
            klog.debug("Add figure: %s", figure_id)
            fig = CinfFigure(figure_def)

            # Add it to the grid layout
            # grid is [row, column, rowspan, columnspan] or [row, column]
            grid = typed(figure_def.find('grid'))
            # Pad 1's for the row and column span if necessary
            grid = grid + [1] * (4 - len(grid))
            klog.debug("Add to grid %s", grid)
            max_column = max(max_column, grid[1] + grid[3] - 1)
            max_row = max(max_row, grid[0] + grid[2] - 1)
            layout.addWidget(fig.native, *grid)

            self.figures[figure_id] = fig

        klog.debug("Add spacer to %s, %s", max_row + 1, max_column + 1)
        layout.addItem(QSpacerItem(1, 1), max_row + 1, max_column + 1)
        layout.setColumnStretch(max_column + 1, 1)
        layout.setRowStretch(max_row + 1, 1)
        self.setLayout(layout)

        klog.debug('show')
        self.showMaximized()

    def update_plot(self):
        """Update the plots"""
        for figure_id, figure in self.figures.items():
            figure.update()

    



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CinfKiosk('kiosksettings.xml',
                   screen_geometry=app.desktop().screenGeometry())
    sys.exit(app.exec_())  

