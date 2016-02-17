""" Control app for analog pressure controller on sniffer setup """
import time
from PyExpLabSys.common.analog_flow_control import AnalogMFC
from PyExpLabSys.common.analog_flow_control import FlowControl

def main():
    """ Main function """

    mfc = AnalogMFC(1, 10, 5)
    mfcs = {}
    mfcs['1'] = mfc

    flow_control = FlowControl(mfcs, 'sniffer')
    flow_control.start()

    while True:
        time.sleep(0.5)

if __name__ == '__main__':
    main()
