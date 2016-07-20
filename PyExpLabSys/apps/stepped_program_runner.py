#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""A general stepped program runner"""

import sys
from os import path
from time import strftime
from PyQt4.QtCore import Qt
from PyQt4.QtGui import (
    QApplication, QCompleter, QLineEdit, QStringListModel, QWidget, QHBoxLayout,
    QVBoxLayout, QPushButton, QTextEdit, QLabel, QScrollArea,
)
from PyQt4 import uic
if sys.version_info[0] >= 3:
    UNICODE_TYPE = str
else:
    UNICODE_TYPE = unicode


NO_FOCUS = Qt.FocusPolicy(0)


class SteppedProgramRunner(QWidget):
    """Main Window"""

    help_texts = {
        'start': 'Start the stepped program',
        'stop': 'Stop the stepped program',
        'quit': 'Quit the stepped program',
        'help': 'Display this help',
    }

    def __init__(self, core, window_title="Stepped Program Runner"):
        super(SteppedProgramRunner, self).__init__()
        self.core = core
        self.completions = ['help']
        self.actions = ['help']
        for action in ('can_start', 'can_stop', 'can_edit_line', 'can_quit'):
            if action in self.core.capabilities:
                self.completions.append(action.replace('can_', ''))
                self.actions.append(action.replace('can_', ''))
        self.status_widgets = {}
        self._init_ui()

    def _init_ui(self):
        """Setup the UI"""
        uifile = path.join(path.dirname(path.realpath(__file__)),
                           'stepped_program_runner.ui')
        uic.loadUi(uifile, self)

        # Setup command line completion
        self.input_line.set_completions(self.completions)
        self.input_line.setFocus()

        # Setup status table
        status = self.status_table
        status.setRowCount(len(self.core.status_fields))
        status.setHorizontalHeaderLabels(['Name', 'Value'])
        for row, (status_codename, status_name) in enumerate(self.core.status_fields):
            status.setCellWidget(row, 0, QLabel(status_name))
            status.setCellWidget(row, 1, QLabel("N/A"))
            self.status_widgets[status_codename] = status.cellWidget(row, 1)
        status.resizeColumnsToContents()

        # HACK to make the table expand to fit the contents, there MUST be a better way
        height = (status.cellWidget(0, 0).size().height() + 16) * (status.rowCount() + 1)
        status.setMinimumHeight(height)

        # Setup step list
        self.step_table.setHorizontalHeaderLabels(['Description'])
        self.update_step_table()

        #self.setWindowTitle('Stepped Program Runner')
        self.show()

    def update_step_table(self):
        """Update the step table"""
        steps = self.core.get_steps()
        if len(steps) != self.step_table.rowCount():
            self.step_table.setRowCount(len(steps))
            self.step_table.setVerticalHeaderLabels([str(n) for n in range(len(steps))])
        for row, (active, step) in enumerate(steps):
            if active:
                step = '<b>' + step + '</b>'
            widget = self.step_table.cellWidget(row, 0)
            if widget:
                widget.setText(step)
            else:
                self.step_table.setCellWidget(row, 0, QLabel(step))

    def process_command(self, command):
        command = UNICODE_TYPE(command).strip()
        self.append_text('<b>{} $ {}</b>'.format(strftime('%H:%M:%S'), command), trail='\n')
        if command.strip() == 'help':
            self.help_text()
        elif command.split(' ')[0] in self.completions:
            self.core.command(command, [])
        else:
            self.append_text('Unknown command: ' + command)

    def append_text(self, text, trail='\n\n'):
        self.text_display.append('<pre>' + text + trail + '</pre>')

    def help_text(self):
        """Form and display help"""
        help_ = ('The stepped program runner is a command driver GUI front for a '
                 'stepped program.\n\n'
                 'For this program the following commands have been configured:\n')
        for action in self.actions:
            help_ += '{: <16}{}\n'.format(action, self.help_texts[action])
        help_ = help_.strip('\n')
        self.append_text(help_)


class LineEdit(QLineEdit):

    def __init__(self, parent = None):    
        QLineEdit.__init__(self, parent)
        self.completer = QCompleter()
        self.setCompleter(self.completer)
        self.model = QStringListModel()
        self.completer.setModel(self.model)
        #get_data(model)
        self.completions = None
        self.parent = parent
    
    def keyPressEvent(self, event):
        text = self.text()
        if event.key() == Qt.Key_Tab:
            current_text = self.text()
            if current_text != '':
                for item in self.completions:
                    if item.startswith(current_text):
                        self.setText(item)
                        break
            event.accept()
        elif event.key() == Qt.Key_Return:
            if text != '':
                self.window().process_command(text)
                self.setText('')
            event.accept()
        else:
            QLineEdit.keyPressEvent(self, event)            

    def set_completions(self, completions):
        """Set completions"""
        self.completions = completions
        self.model.setStringList(completions)



if __name__ == "__main__":

    app = QApplication(sys.argv)
    main_window = SteppedProgramRunner()
    sys.exit(app.exec_())
