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

    def value(self):
        """ Helper function for the reactor logger functionality """
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
                if mfc == 'M11200362H':
                    print "Pressure: " + str(flow)
                    self.reactor_pressure = flow

devices = ['M11200362H', 'M11200362C', 'M11200362A',
           'M11200362E', 'M11200362D', 'M11210022B', 'M11200362G']
ranges = {}

ranges['M11200362H'] = 2.5 # Pressure controller
ranges['M11200362C'] = 10 # Flow1
ranges['M11200362A'] = 10 # Flow2
ranges['M11200362E'] = 5 # Flow3
ranges['M11200362D'] = 5 # Flow4
ranges['M11210022B'] = 10 # Flow5 (NH3 compatible)
ranges['M11200362G'] = 1 # Flow6
name = {}

MFCs = {}
print '!'
for i in range(0, 8):
    error = 0
    name[i] = ''
    while (error < 3) and (name[i]==''):
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
        print error
        print name[i]
    ioerror = 0
    if name[i] in devices:
        while ioerror < 100:
            try:
                MFCs[name[i]] = bronkhorst.Bronkhorst('/dev/ttyUSB' + str(i),
                                                      ranges[name[i]])
                break
            except IOError:
                ioerror = ioerror + 1
        if ioerror == 100:
            print('Fatal error!')

        MFCs[name[i]].set_control_mode() #Accept setpoint from rs232
        print name[i]

Datasocket = DateDataPullSocket(unichr(0x03BC) + '-reactor_mfc_control',
                                devices, timeouts=[3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0],
                                port=9000)
Datasocket.start()

Pushsocket = DataPushSocket(unichr(0x03BC) + '-reactor_mfc_control',
                            action='enqueue')
Pushsocket.start()
Livesocket = LiveSocket(unichr(0x03BC) + '-reactor_mfc_control', devices)
Livesocket.start()

fc = FlowControl(MFCs, Datasocket, Pushsocket, Livesocket)
fc.start()

Logger = ValueLogger(fc, comp_val=1, comp_type='log', low_comp=0.0001)
Logger.start()

codename = 'microreactorng_pressure_reactor'
db_logger = ContinuousLogger(table='dateplots_microreactorNG',
                             username=credentials.user,
                             password=credentials.passwd,
                             measurement_codenames=[codename])
db_logger.start()

time.sleep(10)

while True:
    time.sleep(0.25)
    v = Logger.read_value()
    if Logger.read_trigged():
        print v
        db_logger.enqueue_point_now(codename, v)
        Logger.clear_trigged()

