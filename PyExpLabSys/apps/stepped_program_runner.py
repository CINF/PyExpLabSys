#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""A general stepped program runner"""

import sys
from PyQt4.QtCore import Qt
from PyQt4.QtGui import (
    QApplication, QCompleter, QLineEdit, QStringListModel, QWidget, QHBoxLayout,
    QVBoxLayout, QPushButton, QTextEdit, QLabel
)
if sys.version_info[0] >= 3:
    UNICODE_TYPE = str
else:
    UNICODE_TYPE = unicode


NO_FOCUS = Qt.FocusPolicy(0)


class SteppedProgramRunner(QWidget):
    """Main Window"""

    def __init__(self, core, window_title="Stepped Program Runner"):
        super(SteppedProgramRunner, self).__init__()
        self.core = core
        self.completions = ['help']
        for action in ('can_remove_line', 'can_add_line', 'can_edit_line',
                       'can_play', 'can_stop', 'can_quit'):
            if action in self.core.capabilities:
                self.completions.append(action.replace('can_', ''))
        self._init_ui()

    def _init_ui(self):
        """Setup the UI"""
        # Add text display widget
        self.text_edit = QLabel()# QTextEdit(self)
        #self.text_edit.setReadOnly(True)
        self.text_edit.setFocusPolicy(NO_FOCUS)
        self.text_edit.setAlignment(Qt.AlignLeft | Qt.AlignBottom)

        # Setup input line
        input_line = LineEdit(self)
        input_line.set_completions(self.completions)
        input_line.setFocus()

        # Make layout
        hbox = QVBoxLayout()
        hbox.addWidget(self.text_edit)
        hbox.addWidget(input_line)
        self.setLayout(hbox)    

        # Generic window stuff
        self.setGeometry(300, 300, 600, 600)
        self.setWindowTitle('Stepped Program Runner')
        self.show()

    def process_command(self, command):
        command = UNICODE_TYPE(command).strip()
        if command.strip() == 'help':
            self.append_text('Very helpfull help text')
        elif command.split(' ')[0] in self.completions:
            self.core.command(command, [])
        else:
            self.append_text('Unknown command: ' + command)

    def append_text(self, text):
        self.text_edit.setText(self.text_edit.text() + '\n' + text + '\n')


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
            print('tab in line')
            current_text = self.text()
            if current_text != '':
                for item in self.completions:
                    if item.startswith(current_text):
                        self.setText(item)
                        break
            event.accept()
        elif event.key() == Qt.Key_Return:
            if text != '':
                self.parent.process_command(text)
                self.setText('')
            event.accept()
        else:
            QLineEdit.keyPressEvent(self, event)
            #completions = set(self.completions)
            #if text.strip() in completions:
            #    completions.remove(text)
            

    def set_completions(self, completions):
        """Set completions"""
        self.completions = completions
        self.model.setStringList(completions)

    #def get_data(self, model):



if __name__ == "__main__":

    app = QApplication(sys.argv)
    main_window = SteppedProgramRunner()
    #main_window.show()
    #edit = LineEdit()
    #completer = QCompleter()
    #edit.setCompleter(completer)

    #model = QStringListModel()
    #completer.setModel(model)
    #get_data(model)

    #edit.show()
    sys.exit(app.exec_())
