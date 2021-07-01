""" Flow controller for microreactor Bronkhorst devices """
from __future__ import print_function
import time
from PyExpLabSys.common.flow_control_bronkhorst import FlowControl
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

def main():
    """ Main function """
    devices = ['M17214588A']
    ranges = {}
    ranges['M17214588A'] = 10 # VHP, pressure controller

    flow_control = FlowControl(devices=devices, ranges=ranges, name='microreactor_mfc_control')
    flow_control.start()

    time.sleep(5)
    while True:
        time.sleep(0.25)

if __name__ == '__main__':
    main()
