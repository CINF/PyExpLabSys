""" Common code for Bronkhorst boxes """
from __future__ import print_function
import threading
import time
import PyExpLabSys.drivers.bronkhorst as bronkhorst
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class FlowControl(threading.Thread):
    """ Keep updated values of the current flow """
    def __init__(self, ranges, devices, name):
        threading.Thread.__init__(self)
        self.devices = devices
        name = {}
        mfcs = {}
        print('!')
        for i in range(0, 8):
            error = 0
            name[i] = ''
            while (error < 3) and (name[i] == ''):
                # Pro forma-range will be update in a few lines
                ioerror = 0
                while ioerror < 100:
                    try:
                        bronk = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 1)
                        break
                    except IOError:
                        ioerror = ioerror + 1

                if ioerror == 100:
                    print('Fatal error!')
                name[i] = bronk.read_serial()
                name[i] = name[i].strip()
                error = error + 1
            if name[i] in devices:
                mfcs[name[i]] = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i),
                                                      ranges[name[i]])
                mfcs[name[i]].set_control_mode() #Accept setpoint from rs232
                print(name[i])

        self.mfcs = mfcs
        self.pullsocket = DateDataPullSocket(name, devices,
                                             timeouts=3.0, port=9000)
        self.pullsocket.start()

        self.pushsocket = DataPushSocket(name, action='enqueue')
        self.pushsocket.start()
        self.livesocket = LiveSocket(name, devices)
        self.livesocket.start()
        self.running = True
        self.reactor_pressure = float('NaN')

    def value(self):
        """ Helper function for the reactor logger functionality """
        return self.reactor_pressure

    def run(self):
        while self.running:
            time.sleep(0.1)
            qsize = self.pushsocket.queue.qsize()
            print("Qsize: " + str(qsize))
            while qsize > 0:
                element = self.pushsocket.queue.get()
                mfc = list(element.keys())[0]
                self.mfcs[mfc].set_flow(element[mfc])
                qsize = self.pushsocket.queue.qsize()

            for mfc in self.mfcs:
                flow = self.mfcs[mfc].read_flow()
                self.pullsocket.set_point_now(mfc, flow)
                self.livesocket.set_point_now(mfc, flow)
                if mfc == self.devices[0]: # First device is considered pressure controller
                    print("Pressure: " + str(flow))
                    self.reactor_pressure = flow
