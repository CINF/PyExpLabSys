from __future__ import print_function
import threading
import time
import PyExpLabSys.drivers.bronkhorst as bronkhorst
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import LiveSocket

class FlowControl(threading.Thread):
    """ Keep updated values of the current flow """
    def __init__(self, mfcs, pullsocket, pushsocket, livesocket):
        threading.Thread.__init__(self)
        self.mfcs = mfcs
        print(mfcs)
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.livesocket = livesocket
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
                mfc = element.keys()[0]
                self.mfcs[mfc].set_flow(element[mfc])
                qsize = self.pushsocket.queue.qsize()

            for mfc in self.mfcs:
                flow =  self.mfcs[mfc].read_flow()
                print(mfc + ': ' + str(flow))
                self.pullsocket.set_point_now(mfc, flow)
                self.livesocket.set_point_now(mfc, flow)

devices = ['M7207303F', 'M7207303J', 'M7207303K', 'M7207303L',
           'M7207303E', 'M7207303N']
           
ranges = {}
ranges['M7207303F'] = 100 # MFCA
ranges['M7207303J'] = 100 # MFCB
ranges['M7207303K'] = 100 # MFCC
ranges['M7207303L'] = 100 # MFCD
ranges['M7207303E'] = 100 # MFCE
ranges['M7207303N'] = 3 # Pressure controller

name = {}

MFCs = {}
for i in range(0, 8):
    error = 0
    name[i] = ''
    while (error < 3) and (name[i]==''):
        # Pro forma-range will be update in a few lines
        bronk = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 1)
        name[i] = bronk.read_serial()
        name[i] = name[i].strip()
        error = error + 1
        print(name[i])
    if name[i] in devices:
        MFCs[name[i]] = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i),
                                              ranges[name[i]])
        MFCs[name[i]].set_control_mode() #Accept setpoint from rs232
        print(name[i])

Datasocket = DateDataPullSocket('XRD_mfc_control',
                                devices, timeouts=[3.0] * len(devices),
                                port=9000)
Datasocket.start()

Pushsocket = DataPushSocket('XRD_mfc_control', action='enqueue')
Pushsocket.start()
Livesocket = LiveSocket('XRD-reactor_mfc_control', devices, 1)
Livesocket.start()

fc = FlowControl(MFCs, Datasocket, Pushsocket, Livesocket)
fc.start()

while True:
    time.sleep(0.2)
