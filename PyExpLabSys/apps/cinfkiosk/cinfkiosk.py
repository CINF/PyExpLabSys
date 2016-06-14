
import logging
logging.basicConfig(level=logging.DEBUG)
import xml.etree.ElementTree as ET

import numpy as np

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout

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


class CinfFigure(object):
    """Custom Vispy figure with a little data handling"""

    def __init__(self, xmlconf):
        self.xmlconf = xmlconf
        size = typed(xmlconf.find('size'))
        self.fig = Fig(size=size)
        print('fig is', self.fig)
        self.axes = self.fig[0, 0]
        self.axes.add_parent
        print('axes is', self.axes)
        self.axes.plot(np.random.randn(2, 10)[0])
        self.native = self.fig.native
        print('native is', self.native)

klog = logging.getLogger('kiosk')
class CinfKiosk(QWidget):
    """Cinf Kiosk main app"""
    
    def __init__(self, settings_file):
        """Init local variables"""
        klog.debug('Init')
        super().__init__()
        self.xml = ET.parse(settings_file).getroot()
        self.figures = {}
        self.init_ui()
        
        
    def init_ui(self):
        """Init the UI"""
        klog.debug('init_ui')
        self.setWindowTitle('Cinfkiosk')
        #self.setWindowIcon(QIcon('web.png'))
        
        # Add graphs
        # FIXME Maybe flowlayout, gridlayout or anchorlayout
        layout = QVBoxLayout()
        for graph in self.xml.findall('graph'):
            figure_id = graph.attrib['id']
            if figure_id in self.figures:
                raise ValueError("Think you da lige a little about")
            klog.debug("Add figure: %s", figure_id)
            fig = CinfFigure(graph)
            position = typed(fig.xmlconf.find('position'))
            layout.addWidget(fig.native)
            #widget.move(*position)
            self.figures[figure_id] = fig

        self.setLayout(layout)

        klog.debug('show')
        self.showMaximized()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = CinfKiosk('kiosksettings.xml')
    sys.exit(app.exec_())  

