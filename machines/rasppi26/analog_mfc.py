""" Control app for analog pressure controller on sniffer setup """
import time
from PyExpLabSys.common.analog_flow_control import AnalogMFC
from PyExpLabSys.common.analog_flow_control import FlowControl

def main():
    """ Main function """

    mfc = AnalogMFC(1, 2, 1.5)
    mfcs = {}
    mfcs['1'] = mfc

    try:
        micro = chr(0x03BC) # Python 3
    except ValueError:
        micro = unichr(0x03BC) # Python 2

    flow_control = FlowControl(mfcs, micro + '-reactor')
    flow_control.start()

    while flow_control.is_alive():
        time.sleep(0.5)

if __name__ == '__main__':
    main()
