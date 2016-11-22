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
    port_brooks = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWDN166-if00-port0'
    devices = ['3F2320902001', '3F2320901001']
    datasocket = DateDataPullSocket('palle_mfc_control', devices,
                                    timeouts=[3.0, 3.0], port=9000)
    datasocket.start()

    pushsocket = DataPushSocket('palle_brooks_push_control', action='enqueue')
    pushsocket.start()

    i = 0
    mfcs = {}
    for i in range(0, 2):
        device = devices[i]
        mfcs[device] = brooks.Brooks(device, port=port_brooks)
        print(mfcs[device].long_address)
        print(mfcs[device].read_flow())

    fc = FlowControl(mfcs, datasocket, pushsocket)
    fc.start()

    while fc.running:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            fc.running = False
            print('stopping, waiting for 2 sek')
            time.sleep(2)
    print('stopped')

if __name__ == '__main__':
    main()
