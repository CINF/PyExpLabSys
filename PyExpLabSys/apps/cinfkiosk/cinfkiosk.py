
import sys
from time import sleep, time, strftime
import logging
import json
from threading import Thread
logging.basicConfig(level=logging.DEBUG)
import xml.etree.ElementTree as ET
import numpy as np
from queue import Queue

MESSAGE_QUEUE = Queue()

# Qt imports
from PyQt4.QtGui import QApplication, QWidget, QVBoxLayout, QGridLayout, QSpacerItem
from PyQt4.QtCore import QTimer, QThread, QTime, QDateTime
from pyqtgraph import PlotWidget, AxisItem, PlotItem

# Websocket imports
from twisted.internet import reactor, ssl
#from twisted.python import log
#log.startLogging(sys.stdout)
from autobahn.twisted.websocket import (
    WebSocketClientProtocol, WebSocketClientFactory, connectWS
)


### XML helpers
def typed(xml):
    """Convert XML value to Python types"""
    type_ = xml.attrib.get('type', None)
    if type_ is None:
        return xml.text

    # The type function may be within brackets
    type_func = getattr(__builtins__, type_.strip('[]'))
    if type_.startswith('['):
        return [type_func(value.strip()) for value in xml.text.split(',')]
    else:
        return type_func(xml.text.strip())


def xmlget(xml, element_name, default):
    """Get like function for xml for elements that may or may not exits"""
    subelement = xml.find(element_name)
    if subelement is not None:
        return typed(subelement)
    else:
        return default


### Graph
# Modified from https://gist.github.com/friendzis/4e98ebe2cf29c0c2c232
class TimeAxisItem(AxisItem):
    def __init__(self, *args, **kwargs):
        super(TimeAxisItem, self).__init__(*args, **kwargs)

    def tickStrings(self, values, scale, spacing):
        """Return HH:mm:ss strings from unixtime values"""
        out = []
        for value in values:
            t = QDateTime()
            t.setTime_t(value)
            out.append(t.toString('HH:mm:ss'))
        return values


def tickStrings(values, scale, spacing):
    """Return HH:mm:ss strings from unixtime values"""
    out = []
    for value in values:
        t = QDateTime()
        t.setTime_t(value)
        out.append(t.toString('HH:mm:ss'))
    return out


clog = logging.getLogger('CinfFigure')
class Cinfpyqtgraph(PlotWidget):
    """Custom pyqtgraph with a little data handling"""

    def __init__(self, parent, xmlconf, background='default'):
        """Initialize local variables"""
        
        # Extract title and labels
        title = xmlget(xmlconf, 'title', None)
        clog.debug('Title: %s', title)
        labels = {}
        for label_element in xmlconf.findall('label'):
            labels[label_element.attrib['position']] = label_element.text

        # Call init on pyqtgraph
        super(Cinfpyqtgraph, self).__init__(
            parent=parent, background=background, title=title, labels=labels,
            # There seems to be a bug in pyqtgraph FIXME
            #axisItems={'top': TimeAxisItem(orientation='top')},
        )
        self.getAxis('bottom').tickStrings = tickStrings

        # Set size
        self.xmlconf = xmlconf
        size = typed(xmlconf.find('size'))
        self.setFixedSize(*size)

        # Set the x window
        self.current_window = None
        self.xwindow = xmlget(xmlconf, "xwindow", 600)
        self.jump_ahead = xmlget(xmlconf, "jump_ahead", 0.2)
        clog.debug('xwindow: %s, jump_ahead: %s', self.xwindow, self.jump_ahead)
        self.set_x_window()

        # Form curves
        self.curves = {}
        self.data = {}
        for curve_def in xmlconf.findall('plot'):
            print(curve_def)
            data_channel = curve_def.find('data_channel').text
            self.curves[data_channel] = self.plot([], [])
            self.data[data_channel] = [[], []]


        print(self.viewRange()[0])

        

    def process_data_batch(self, data):
        host = data['host']
        for codename, value in data['data'].items():
            sub_def = '{}:{}'.format(host, codename)
            curve = self.curves.get(sub_def)
            if curve is not None:
                self.data[sub_def][0].append(value[0])
                self.data[sub_def][1].append(value[1])
                curve.setData(*self.data[sub_def])
                if value[0] > self.current_window[1]:
                    self.set_x_window()
                    self.shave_data()

    def set_x_window(self):
        """Set the X-window"""
        now = time()
        self.current_window = (
            now - self.xwindow * (1 - self.jump_ahead), now + self.xwindow * self.jump_ahead
        )
        self.setXRange(*self.current_window)

    def shave_data(self):
        """Shave old data off the list"""
        xstart = self.current_window[0]
        for sub_def, data in self.data.items():
            for n, value in enumerate(data[0]):
                if value > xstart:                    
                    cut = max(n - 1, 0)
                    break
            else:
                cut = 0
            if cut != 0:
                print('Shave', cut, len(data[0]))
                data[0] = data[0][cut:]
                data[1] = data[1][cut:]




klog = logging.getLogger('kiosk')
class AThread(QThread):

    def run(self):
        """Main threaded method"""
        klog.info("run in data thread started")
        cinfkiosk = self.parent()

        MESSAGE_QUEUE.put(cinfkiosk.subscriptions)
        while MESSAGE_QUEUE.qsize() > 0:
            sleep(1E-6)

        while True:
            item = MESSAGE_QUEUE.get()
            #klog.debug('Got data item %s', item)
            if item == 'STOP':
                break
            cinfkiosk.process_data_batch(item)
        klog.info('run in data thread stopped')



class CinfKiosk(QWidget):
    """Cinf Kiosk main app"""
    
    def __init__(self, settings_file, screen_geometry):
        """Init local variables"""
        klog.debug('Init')
        super(CinfKiosk, self).__init__()
        self.xml = ET.parse(settings_file).getroot()
        self.screen_geometry = screen_geometry
        #self.setGeometry(300, 300, 1000, 1000)
        self.figures = {}
        self.init_ui()

        self.subscriptions = set()
        #self.parse_subscriptions()
        self.subscriptions = {
            u'action': u'subscribe',
            u'subscriptions': [u'rasppi71:thetaprobe_main_chamber_pressure',
                               u'rasppi25:thetaprobe_pressure_loadlock',
                               u'rasppi71:thetaprobe_load_lock_roughing_pressure',
                               u'rasppi71:thetaprobe_main_chamber_temperature']
        }


        self.data_thread = AThread(self)
        #thread.finished.connect(app.exit)
        self.data_thread.start()
        #sys.exit(app.exec_())
        
        
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
            fig = Cinfpyqtgraph(self, figure_def)

            # Add it to the grid layout
            # grid is [row, column, rowspan, columnspan] or [row, column]
            grid = typed(figure_def.find('grid'))
            # Pad 1's for the row and column span if necessary
            grid = grid + [1] * (4 - len(grid))
            klog.debug("Add to grid %s", grid)
            max_column = max(max_column, grid[1] + grid[3] - 1)
            max_row = max(max_row, grid[0] + grid[2] - 1)
            layout.addWidget(fig, *grid)

            self.figures[figure_id] = fig

        klog.debug("Add spacer to %s, %s", max_row + 1, max_column + 1)
        layout.addItem(QSpacerItem(1, 1), max_row + 1, max_column + 1)
        layout.setColumnStretch(max_column + 1, 1)
        layout.setRowStretch(max_row + 1, 1)
        self.setLayout(layout)

        klog.debug('show')
        self.showMaximized()
        self.show()

    def process_data_batch(self, databatch):
        """Receive data"""
        for fig in self.figures.values():
            fig.process_data_batch(databatch)

    def closeEvent(self, event):
        klog.info('close event')
        MESSAGE_QUEUE.put('STOP')
        while self.data_thread.isRunning():
            sleep(1E-6)
        super(CinfKiosk, self).closeEvent(event)
        


WEBSOCKET_CLIENT = None
wslog = logging.getLogger('WebSocket')
class MyClientProtocol(WebSocketClientProtocol):

    def onConnect(self, response):
        """onConnection call back"""
        global WEBSOCKET_CLIENT
        WEBSOCKET_CLIENT = self
        wslog.debug("Server connected: %s", response.peer)

    def onOpen(self):
        subscribe = MESSAGE_QUEUE.get()
        self.sendMessage(json.dumps(subscribe).encode('ascii'))
        wslog.debug("WebSocket connection open.")

    def onMessage(self, payload, isBinary):

        MESSAGE_QUEUE.put(json.loads(payload.decode('utf8')))
        #wslog.debug("Text message received: %s", payload.decode('utf8'))

    def onClose(self, wasClean, code, reason):
        wslog.debug("WebSocket connection closed: %s", reason)


if __name__ == '__main__':
    factory = WebSocketClientFactory(url="wss://cinf-wsserver.fysik.dtu.dk:9002")
    factory.protocol = MyClientProtocol

    if factory.isSecure:
        contextFactory = ssl.ClientContextFactory()
    else:
        contextFactory = None

    connectWS(factory, contextFactory)
    Thread(target=reactor.run, args=(False,)).start()
    #t = MyThread(reactor)

    app = QApplication(sys.argv)
    ex = CinfKiosk('kiosksettings.xml',
                   screen_geometry=app.desktop().screenGeometry())
    ret = app.exec_()

    # Stop websocket connection and reactor
    WEBSOCKET_CLIENT.sendClose()
    while WEBSOCKET_CLIENT.state != WEBSOCKET_CLIENT.STATE_CLOSED:
        sleep(1E-3)
    reactor.stop()

    sys.exit(ret)

