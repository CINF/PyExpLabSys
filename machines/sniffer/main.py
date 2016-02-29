# pylint: disable=invalid-name

"""UBD test app"""

from __future__ import print_function

import os
import sys
import json
import time
from functools import partial
from collections import deque
from PyQt4 import QtGui, QtCore
from ubd.pyqt import loader
from flow_temp_core import FlowTempCore

# Dict of codenames pointing towards UI widget variables
CODENAMES_TO_WIDGETS = {
    '21984878': 'value0',
    '21984877': 'value1',
    '21984876': 'value2',
    '21984879': 'value3',
}
# Dict of UI widget variables pointing towards codenames
WIDGETS_TO_CODENAMES = {}
for key, value in CODENAMES_TO_WIDGETS.items():
    widget_name = 'setpoint' + value[-1]
    WIDGETS_TO_CODENAMES[widget_name] = key


def names(prefix, upper_bound):
    """Return a strings with prefix followed by number up to upper_bound"""
    return [prefix + str(number) for number in range(upper_bound)]


class MyWindow(QtGui.QMainWindow):
    """My Window test class"""
    def __init__(self):
        super(MyWindow, self).__init__()
        loader.loadUi('flows_and_temperatures.ui', self)
        self.show()

        # Initialize internal parameters
        self.log_messages = deque(maxlen=10)
        self.log('GUI loaded')

        # Bind changes in flow widgets to flow change
        self.bindings_to_disconnect = []
        for name in names('setpoint', 6):
            widget = getattr(self, name)
            # Make the widgets pass their name as the first argument in the callback
            callback = partial(self.flow_change, name)
            widget.editingFinished.connect(callback)
            self.bindings_to_disconnect.append((widget.editingFinished, callback))
        self.log('Flow call backs setup')

        # Bind buttons
        self.load_flow_file_btn.clicked.connect(self.load_flow_file)
        self.start_flow_file_btn.clicked.connect(self.start_flow_file)
        self.stop_flow_file_btn.clicked.connect(self.stop_flow_file)

        # Reload gui values
        try:
            with open('gui_memory.json') as file_:
                gui_memory = json.loads(file_.read())
                for name, description in gui_memory.items():
                    getattr(self, name).setText(description)
                self.flow_file.setText(gui_memory['flow_file'])
            self.log('Gui memory reloaded from json file')
        except IOError:
            pass

        # Initialize the core
        self.flow_temp_core = FlowTempCore(self)
        
        # Start update flows timer
        self.flows_timer = QtCore.QTimer(self)
        self.flows_timer.timeout.connect(self.update_flows)
        self.flows_timer.start(100)
        

    def flow_change(self, widget_name):
        """Pass on a flow change to hardware"""
        value = getattr(self, widget_name).value()
        print(repr(value))
        codename = WIDGETS_TO_CODENAMES[widget_name]
        self.flow_temp_core.set_flow(codename, value)
        self.log('{} changed to {}', widget_name, value)

    def closeEvent(self, event):
        """Close the program"""
        self.flows_timer.stop()
        self.flow_temp_core.stop()
        # Write descriptions out to file
        gui_memory = {}
        for name in names('description', 6):
            gui_memory[name] = str(getattr(self, name).text())
        gui_memory['flow_file'] = str(self.flow_file.text())
        with open('gui_memory.json', 'w') as file_:
            file_.write(json.dumps(gui_memory))
        self.log('GUI memory written to json file, now close')

        # Disconnect flow bindings
        for signal, callback in self.bindings_to_disconnect:
            signal.disconnect(callback)

        event.accept()

    def load_flow_file(self):
        """Load a flow file"""
        current_dir = os.path.dirname(os.path.realpath(__file__))
        filepath = str(QtGui.QFileDialog.getOpenFileName(
                self, caption='Open flow file', directory=current_dir,
                filter="Flow files (*.flow *.txt)"
            ))
        if filepath == '':
            self.log('File load aborted')
            return

        self.log('File "{}" loaded', filepath)
        self.flow_file.setText(os.path.relpath(filepath))

    def start_flow_file(self):
        """Start the currently loaded flow file"""
        flow_file = str(self.flow_file.text())
        if flow_file == '':
            QtGui.QDialog('Load flow file first')
            return
        self.log('Start flow file')
        self.flow_temp_core.start_flow_file(os.path.abspath(flow_file))
        self.log('Started flow file')

    def stop_flow_file(self):
        """Stop the currently running flow file"""
        self.log('Stop flow file')
        self.flow_temp_core.stop_flow_file()

    def log(self, message, *args, **kwargs):
        """Log message to log window

        Will be formatted like message.format(*args, **kwargs)
        """
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        logmessage = '{} {}'.format(timestamp, message.format(*args, **kwargs))
        #print(logmessage)
        self.log_messages.appendleft(logmessage)
        self.logtext.setText('\n'.join(self.log_messages))

    def update_flows(self):
        """Updating flows"""
        flows = self.flow_temp_core.get_flows()
        for key, value in CODENAMES_TO_WIDGETS.items():
            # key, value is e.g. '21984878', 'value0'
            widget = getattr(self, value)
            widget.display(flows[key][1])


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    mywin = MyWindow()
    sys.exit(app.exec_())
