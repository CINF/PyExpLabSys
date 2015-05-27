# pylint: disable=invalid-name

"""This file contains the core set flow and and control temperature logic"""

from __future__ import print_function
from time import sleep
from ubd.pyqt.threaded_methods import ThreadedMethod


class FlowTempCore(object):
    """Main flow and temperature control class"""

    def __init__(self, ui):
        self.ui = ui

    def set_flow(self, flow_name, value):
        """Send value for flow_name to control box"""
        print('### Send', value, 'to', flow_name)

    @ThreadedMethod
    def start_flow_file(self, filepath):
        """Start the flow file"""
        print('### Start flow file' + filepath)
        print('sleep 2')
        sleep(2)
        print('done')

    def stop_flow_file(self):
        """Stop running the active flow file"""
        print('### Stop flow file')



if __name__ == '__main__':
    raise RuntimeError("Run main.py instead")
