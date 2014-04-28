# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'simple_plot.ui'
#
# Created: Wed Feb 26 10:55:04 2014
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

class Ui_PlotTest(object):
    def setupUi(self, PlotTest):
        PlotTest.setObjectName(_fromUtf8("PlotTest"))
        PlotTest.resize(965, 585)
        self.horizontalLayoutWidget = QtGui.QWidget(PlotTest)
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
        self.scale_spinbutton = QtGui.QSpinBox(self.horizontalLayoutWidget)
        self.scale_spinbutton.setMinimum(-18)
        self.scale_spinbutton.setMaximum(18)
        self.scale_spinbutton.setProperty("value", -8)
        self.scale_spinbutton.setObjectName(_fromUtf8("scale_spinbutton"))
        self.verticalLayout.addWidget(self.scale_spinbutton)
        self.scale_label = QtGui.QLabel(self.horizontalLayoutWidget)
        self.scale_label.setObjectName(_fromUtf8("scale_label"))
        self.verticalLayout.addWidget(self.scale_label)
        self.quit_button = QtGui.QPushButton(self.horizontalLayoutWidget)
        self.quit_button.setObjectName(_fromUtf8("quit_button"))
        self.verticalLayout.addWidget(self.quit_button)
        self.horizontalLayout.addLayout(self.verticalLayout)

        self.retranslateUi(PlotTest)
        QtCore.QMetaObject.connectSlotsByName(PlotTest)

    def retranslateUi(self, PlotTest):
        PlotTest.setWindowTitle(_translate("PlotTest", "Form", None))
        self.start_button.setText(_translate("PlotTest", "Start", None))
        self.stop_button.setText(_translate("PlotTest", "Stop", None))
        self.scale_label.setText(_translate("PlotTest", "1E-8", None))
        self.quit_button.setText(_translate("PlotTest", "Quit", None))

