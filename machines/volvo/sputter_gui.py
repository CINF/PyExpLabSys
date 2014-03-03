# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'sputter_gui.ui'
#
# Created: Fri Feb 28 14:37:04 2014
#      by: PyQt4 UI code generator 4.10.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Specs(object):
    def setupUi(self, Specs):
        Specs.setObjectName(_fromUtf8("Specs"))
        Specs.resize(965, 585)
        self.horizontalLayoutWidget = QtGui.QWidget(Specs)
        self.horizontalLayoutWidget.setGeometry(QtCore.QRect(0, 10, 961, 571))
        self.horizontalLayoutWidget.setObjectName(_fromUtf8("horizontalLayoutWidget"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setMargin(0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.start_button = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.start_button.setObjectName(_fromUtf8("start_button"))
        self.verticalLayout.addWidget(self.start_button)
        self.stop_button = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.stop_button.setObjectName(_fromUtf8("stop_button"))
        self.verticalLayout.addWidget(self.stop_button)
        self.sputter_current = QtGui.QSpinBox(self.horizontalLayoutWidget)
        self.sputter_current.setMinimum(-99999)
        self.sputter_current.setMaximum(999999)
        self.sputter_current.setProperty("value", 0)
        self.sputter_current.setObjectName(_fromUtf8("sputter_current"))
        self.verticalLayout.addWidget(self.sputter_current)
        self.filament_bias = QtGui.QLineEdit(self.horizontalLayoutWidget)
        self.filament_bias.setObjectName(_fromUtf8("filament_bias"))
        self.verticalLayout.addWidget(self.filament_bias)
        self.scale_label = QtGui.QLabel(self.horizontalLayoutWidget)
        self.scale_label.setObjectName(_fromUtf8("scale_label"))
        self.verticalLayout.addWidget(self.scale_label)
        self.quit_button = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.quit_button.setObjectName(_fromUtf8("quit_button"))
        self.verticalLayout.addWidget(self.quit_button)
        self.horizontalLayout.addLayout(self.verticalLayout)

        self.retranslateUi(Specs)
        QtCore.QMetaObject.connectSlotsByName(Specs)

    def retranslateUi(self, Specs):
        Specs.setWindowTitle(_translate("Specs", "Form", None))
        self.start_button.setText(_translate("Specs", "Start", None))
        self.stop_button.setText(_translate("Specs", "Stop", None))
        self.scale_label.setText(_translate("Specs", "1E-8", None))
        self.quit_button.setText(_translate("Specs", "Quit", None))

