import threading
import time
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import LiveSocket
from ABE_ADCDACPi import ADCDACPi

class AnalogMFC():
    def __init__(self, channel, fullrange, voltagespan, daq):
        self.channel = channel
        self.fullrange = fullrange
        self.voltagespan = voltagespan
        self.daq = daq

    def read_flow(self):
        value = self.daq.read_adc_voltage(1)
        flow = value * self.fullrange / self.voltagespan
        return flow


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
                print(mfc + ': ' + str(flow))
                self.pullsocket.set_point_now(mfc, flow)
                self.livesocket.set_point_now(mfc, flow)

adcdac = ADCDACPi()  # create an instance of ADCDACPi
adcdac.set_adc_refvoltage(3.3)

devices = ['1']
MFC = AnalogMFC(1, 2, 2, adcdac)
MFCs = {}
MFCs['1'] = MFC

Datasocket = DateDataPullSocket('microreactor_mfc_control',
                                devices,
                                timeouts=[3.0],
                                port=9000)
Datasocket.start()

Pushsocket = DataPushSocket(unichr(0x03BC) + '-reactor_analog_mfc_control',
                            action='enqueue')
Pushsocket.start()
Livesocket = LiveSocket(unichr(0x03BC) + '-reactor_analog_mfc_control',
                        devices, 1)
Livesocket.start()

fc = FlowControl(MFCs, Datasocket, Pushsocket, Livesocket)
fc.start()

while True:
    time.sleep(0.5)
