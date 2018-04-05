""" Flow control for Palle MKS MFCs """
from __future__ import print_function
import threading
import time
import PyExpLabSys.drivers.mks_g_series as mks_g_series
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class FlowControl(threading.Thread):
    """ Keep updated values of the current flow """
    def __init__(self, mks_instance, mfcs, devices, name):
        threading.Thread.__init__(self)
        self.mfcs = mfcs
        self.mks = mks_instance
        self.pullsocket = DateDataPullSocket(name, devices, timeouts=3.0, port=9000)
        self.pullsocket.start()

        self.pushsocket = DataPushSocket(name, action='enqueue')
        self.pushsocket.start()

        self.livesocket = LiveSocket(name, devices)
        self.livesocket.start()
        self.running = True

    def run(self):
        while self.running:
            time.sleep(0.1)
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                element = self.pushsocket.queue.get()
                mfc = list(element.keys())[0]
                print(element[mfc])
                print('Queue: ' + str(qsize))
                self.mks.set_flow(element[mfc], self.mfcs[mfc])
                qsize = self.pushsocket.queue.qsize()

            for mfc in self.mfcs:
                print('!!!')
                flow = self.mks.read_flow(self.mfcs[mfc])
                print(mfc + ': ' + str(flow))
                self.pullsocket.set_point_now(mfc, flow)
                self.livesocket.set_point_now(mfc, flow)


def main():
    """ Main function """
    port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWGRKWL-if00-port0'
    devices = ['22194266', '22194267']
    name = 'microreactor_mks_mfc_control'

    i = 0
    mfcs = {}
    mks = mks_g_series.MksGSeries(port=port)
    for i in range(1, 8):
        time.sleep(2)
        print('!')
        serial = mks.read_serial_number(i)
        print(serial)
        if serial in devices:
            mfcs[serial] = i

    flow_control = FlowControl(mks, mfcs, devices, name)
    flow_control.start()

    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
