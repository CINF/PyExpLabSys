# pylint: disable=R0913, C0103

import threading
import time
import PyExpLabSys.drivers.bronkhorst as bronkhorst
from PyExpLabSys.common.loggers import ContinuousLogger
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import LiveSocket
import credentials

class FlowControl(threading.Thread):
    """ Keep updated values of the current flow """
    def __init__(self, mfcs, pullsocket, pushsocket, livesocket):
        threading.Thread.__init__(self)
        self.mfcs = mfcs
        print mfcs
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.livesocket = livesocket
        self.running = True
        self.reactor_pressure = float('NaN')

    def value(self, channel):
        """ Helper function for the reactor logger functionality """
        if channel == 1:
            return self.reactor_pressure

    def run(self):
        while self.running:
            time.sleep(0.1)
            qsize = self.pushsocket.queue.qsize()
            print "Qsize: " + str(qsize)
            while qsize > 0:
                element = self.pushsocket.queue.get()
                mfc = element.keys()[0]
                self.mfcs[mfc].set_flow(element[mfc])
                qsize = self.pushsocket.queue.qsize()

            for mfc in self.mfcs:
                flow =  self.mfcs[mfc].read_flow()
                #print(mfc + ': ' + str(flow))
                self.pullsocket.set_point_now(mfc, flow)
                self.livesocket.set_point_now(mfc, flow)
                if mfc == 'M11210022A':
                    print "Pressure: " + str(flow)
                    self.reactor_pressure = flow

#port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTWGRR44-if00-port0'
devices = ['M11210022A']
ranges = {}
ranges['M11210022A'] = 2.5 #Sniffer

name = {}

MFCs = {}
print '!'
for i in range(0, 8):
    error = 0
    name[i] = ''
    while (error < 3) and (name[i]==''):
        # Pro forma-range will be update in a few lines
        bronk = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i), 1) 
        name[i] = bronk.read_serial()
        name[i] = name[i].strip()
        error = error + 1
    if name[i] in devices:
        MFCs[name[i]] = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i),
                                              ranges[name[i]])
        MFCs[name[i]].set_control_mode() #Accept setpoint from rs232
        print name[i]

Datasocket = DateDataPullSocket('sniffer_mfc_control',
                                devices,
                                timeouts=[3.0],
                                port=9000)
Datasocket.start()

Pushsocket = DataPushSocket('sniffer_mfc_control', action='enqueue')
Pushsocket.start()
Livesocket = LiveSocket('sniffer_mfc_control', devices)
Livesocket.start()

fc = FlowControl(MFCs, Datasocket, Pushsocket, Livesocket)
fc.start()

Logger = ValueLogger(fc, comp_val=1, comp_type='log', low_comp=0.0001, channel=1)
Logger.start()

db_logger = ContinuousLogger(table='dateplots_sniffer',
                             username=credentials.user,
                             password=credentials.passwd,
                             measurement_codenames=['sniffer_chip_pressure'])
db_logger.start()

time.sleep(5)
while True:
    time.sleep(0.25)
    v = Logger.read_value()
    if Logger.read_trigged():
        print v
        db_logger.enqueue_point_now('sniffer_chip_pressure', v)
        Logger.clear_trigged()


