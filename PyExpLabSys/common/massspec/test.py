"""Module to test the mass spec common components"""


import sys
from PyQt4 import QtGui, QtCore
from channel import MSChannel
from qt import QtMSChannel


class Test(QtGui.QWidget):
    """ Class to test the QtMSChannel """
    def __init__(self):
        super(Test, self).__init__()
        self.channel = QtMSChannel(self, 10)
        self.widgets = {}

        grid = QtGui.QGridLayout()

        grid.addWidget(self.channel.gui('active'))

        self.setLayout(grid)
        self.show()


def testgui():
    """Test the gui"""
    app = QtGui.QApplication(sys.argv)
    test = Test()
    sys.exit(app.exec_())


def testchannel():
    """Test the channels"""
    print "Test __str__ for channel for mass 10"
    channel1 = Channel(10.1)
    print channel1

    print '\nTest of to_dict'
    channel1_dict = channel1.to_dict
    print channel1_dict

    print '\nTest of from dict, change mass to 12'
    channel1_dict['mass'] = 12.0
    channel2 = Channel.from_dict(channel1_dict)
    print channel2
    

if __name__ == '__main__':
    testchannel()
