#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""A general stepped program runner"""

import sys
from os import path
from time import strftime, sleep
import traceback
from functools import partial
# Python 2-3 hacks
if sys.version_info[0] >= 3:
    UNICODE_TYPE = str
else:
    UNICODE_TYPE = unicode
try:
    import Queue
except ImportError:
    import queue as Queue

from PyQt4.QtCore import Qt, QTimer, QCoreApplication
from PyQt4.QtGui import (
    QApplication, QCompleter, QLineEdit, QStringListModel, QWidget, QHBoxLayout,
    QVBoxLayout, QPushButton, QTextEdit, QLabel, QScrollArea,
)
from PyQt4 import uic
NO_FOCUS = Qt.FocusPolicy(0)


class SteppedProgramRunner(QWidget):
    """Main Window"""

    help_texts = {
        'start': 'Start the stepped program',
        'stop': 'Stop the stepped program',
        'quit': 'Quit the stepped program. This will ask the core program to stop, wait for it t do so and quit the main GUI',
        'help': 'Display this help',
    }

    def __init__(self, core, window_title="Stepped Program Runner"):
        super(SteppedProgramRunner, self).__init__()
        self.core = core
        self.last_text_type = 'none'
        self.completions = ['help']
        self.actions = ['help']
        for action in ('can_start', 'can_stop', 'can_edit_line', 'can_quit'):
            if action in self.core.capabilities:
                self.completions.append(action.replace('can_', ''))
                self.actions.append(action.replace('can_', ''))
        self.status_widgets = {}
        self._init_ui()
        self.process_update_timer = QTimer()
        self.process_update_timer.timeout.connect(self.process_updates)
        self.process_update_timer.start(100)
        self.quit_timer = QTimer()
        self.quit_timer.timeout.connect(self.process_quit)

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

        title = getattr(self.core, 'config', {}).get('program_title')
        if title:
            self.setWindowTitle(title)
        self.show()

    def process_updates(self):
        """Process updates from the main program"""
        while True:
            try:
                update_type, update_content = self.core.message_queue.get(True, 0.001)
                if update_type == 'steps':
                    self.update_step_table(update_content)
                elif update_type == 'status':
                    self.update_status(update_content)
                elif update_type == 'message':
                    self.append_text(update_content, text_type='message')
            except Queue.Empty:
                break
        self.process_update_timer.start(100)

    def update_step_table(self, steps):
        """Update the step table"""
        # Allow for changing number of steps
        if len(steps) != self.step_table.rowCount():
            self.step_table.setRowCount(len(steps))
            self.step_table.setVerticalHeaderLabels([str(n) for n in range(len(steps))])
        # Write out the steps
        for row, (active, step) in enumerate(steps):
            if active:
                step = '<b>' + step + '</b>'
            widget = self.step_table.cellWidget(row, 0)
            if widget:
                widget.setText(step)
            else:
                self.step_table.setCellWidget(row, 0, QLabel(step))

    def update_status(self, status):
        """Update the status table"""
        try:
            for codename, value in status.items():
                try:
                    widget = self.status_widgets[codename]
                except KeyError:
                    message = 'Unknow field "{}" in status update'.format(codename)
                    self.append_text(message, text_type='error')
                else:
                    widget.setText(UNICODE_TYPE(value))
        except Exception:
            text = ('An unknown error accoured during updating of the status table\n'
                    'It had the following traceback\n' + traceback.format_exc())
            self.append_text(text, text_type='error')

    def process_command(self, command):
        """Process a command"""
        command = UNICODE_TYPE(command).strip()
        self.append_text(command, text_type='command')
        splitted_command = command.split(' ')
        if command == 'help':
            self.help_text()
        elif command == 'quit':
            self.process_quit(first_call=True)
        elif splitted_command[0] in self.completions:
            args = ' '.join(splitted_command[1:])
            try:
                self.core.command(splitted_command[0], args)
            except Exception:
                text = ('An error occoured during the execution of the command\n'
                        'It had the following traceback\n' + traceback.format_exc())
                self.append_text(text, text_type='error')
        else:
            self.append_text('Unknown command: ' + command, start='\n')

    def append_text(self, text, start='\n\n', text_type=None):
        """Append text to the text_display"""
        # Always append text immediately after command
        if self.last_text_type == 'command' and text_type != 'command':
            start = '\n'

        # Format depending on text_type
        if text_type == 'error':
            text = '<b><span style="color:#ff0000;">Error: {}</span></b>'.format(text)
        elif text_type == 'message':
            # Append several message from core right after each other
            if self.last_text_type == 'message':
                start = '\n'
            text = '<b><span style="color:#0000ff;">{} says: {}</span></b>'.format(
                self.core.__class__.__name__, text
            )
        elif text_type == 'command':
            text = '<b>{} $ {}</b>'.format(strftime('%H:%M:%S'), text)

        # Set last text_type and display
        self.last_text_type = text_type
        self.text_display.append('<pre>' + start + text + '</pre>')

    def help_text(self):
        """Form and display help"""
        help_ = ('The stepped program runner is a command driver GUI front for a '
                 'stepped program.\n\n'
                 'For this program the following commands have been configured:\n')
        for action in self.actions:
            help_ += '{: <16}{}\n'.format(action, self.help_texts[action])
        help_ = help_.strip('\n')
        self.append_text(help_, start='\n')

    def process_quit(self, first_call=False, quit_now=False):
        """Process the quit command"""
        if quit_now:
            QCoreApplication.instance().quit()
            return
        if first_call:
            text = "Quitting."
            if self.core.isAlive() and 'can_stop' in self.core.capabilities:
                text += ' Asking stepped program to stop and wait for it to do so.'
                self.append_text(text)
                self.core.command('stop', '')
            else:
                self.append_text(text)

        if self.core.isAlive():
            self.quit_timer.start(100)
        else:
            self.append_text('<b>Bye!</b>')
            self.quit_timer.timeout.disconnect()
            self.quit_timer.timeout.connect(partial(self.process_quit, quit_now=True))
            self.quit_timer.start(1000)
            
    def closeEvent(self, event):
        """Make sure to close down nicely on window close"""
        event.ignore()
        self.process_quit(first_call=True)



class LineEdit(QLineEdit):
    """Cursom QLineEdit with tab completion"""

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
