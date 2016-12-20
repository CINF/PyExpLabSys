""" MFC Control for VHP """
from __future__ import print_function
import threading
import time
import PyExpLabSys.drivers.brooks_s_protocol as brooks
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)


class FlowControl(threading.Thread):
    """ Keep updated values of the current flow """
    def __init__(self, mfcs, pullsocket, pushsocket):
        threading.Thread.__init__(self)
        self.mfcs = mfcs
        print(mfcs)
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.running = True

    def run(self):
        while self.running:
            time.sleep(0.1)
            qsize = self.pushsocket.queue.qsize()
            print(qsize)
            while qsize > 0:
                element = self.pushsocket.queue.get()
                mfc = element.keys()[0]
                self.mfcs[mfc].set_flow(element[mfc])
                qsize = self.pushsocket.queue.qsize()

            for mfc in self.mfcs:
                flow = self.mfcs[mfc].read_flow()
                #print(mfc + ': ' + str(flow))
                self.pullsocket.set_point_now(mfc, flow)


def main():
    """ Main function """
    port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWGRR44-if00-port0'
    devices = ['F25600004', 'F25600005', 'F25600006', 'F25600001', 'F25600002',
               'F25600003', 'F25698001']
    datasocket = DateDataPullSocket('vhp_mfc_control', devices, timeouts=3, port=9000)
    datasocket.start()

    pushsocket = DataPushSocket('vhp_push_control', action='enqueue')
    pushsocket.start()

    mfcs = {}
    for device in devices:
        mfcs[device] = brooks.Brooks(device, port=port)
        print(mfcs[device].read_flow())

    flow_control = FlowControl(mfcs, datasocket, pushsocket)
    flow_control.start()

    while flow_control.isAlive():
        time.sleep(0.5)

if __name__ == '__main__':
    main()
