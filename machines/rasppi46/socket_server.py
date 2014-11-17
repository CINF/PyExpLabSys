# pylint: disable=R0913,W0142,C0103 

import threading
import time
import PyExpLabSys.drivers.brooks_s_protocol as brooks
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket

""" This really should be moved to a common module """
class FlowControl(threading.Thread):
    """ Keep updated values of the current flow """
    def __init__(self, mfcs, pullsocket, pushsocket):
        threading.Thread.__init__(self)
        self.mfcs = mfcs
        print mfcs
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.running = True

    def run(self):
        while self.running:
            time.sleep(0.1)
            qsize = self.pushsocket.queue.qsize()
            print qsize
            while qsize > 0:
                element = self.pushsocket.queue.get()
                mfc = element.keys()[0]
                self.mfcs[mfc].set_flow(element[mfc])
                qsize = self.pushsocket.queue.qsize()

            for mfc in self.mfcs:
                flow =  self.mfcs[mfc].read_flow()
                #print(mfc + ': ' + str(flow))
                self.pullsocket.set_point_now(mfc, flow)


port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWGRIPE-if00-port0'
devices = ['F25969001', 'F25969002', 'F23968002']
datasocket = DateDataPullSocket('cr_mfc_control',
                                devices,
                                timeouts=[3.0, 3.0, 3.0],
                                port=9000)
datasocket.start()

pushsocket = DataPushSocket('cr_push_control', action='enqueue')
pushsocket.start()

i = 0
mfcs = {}
for device in devices:
    mfcs[device] = brooks.Brooks(device, port=port)
    print mfcs[device].long_address
    print mfcs[device].read_flow()

fc = FlowControl(mfcs, datasocket, pushsocket)
fc.start()

while True:
    pass

