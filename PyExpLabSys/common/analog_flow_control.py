""" Control app for analog pressure controller on sniffer setup """
from __future__ import print_function
import threading
import time
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import LiveSocket
try:
    from ABE_ADCDACPi import ADCDACPi
except ImportError:
    # Newer versions of ABElectronics Python code import from this location
    from ADCDACPi import ADCDACPi

class AnalogMFC(object):
    """ Driver for controling an analog MFC (or PC) with
    an AB Electronics ADCDAC """
    def __init__(self, channel, fullrange, voltagespan):
        self.channel = channel
        self.fullrange = fullrange
        self.voltagespan = voltagespan
        self.daq = ADCDACPi()  # create an instance of ADCDACPi
        self.daq.set_adc_refvoltage(3.3)

    def read_flow(self):
        """ Read the flow (or pressure) value """
        value = 0
        for _ in range(0, 10): # Average to minimiza noise
            value += self.daq.read_adc_voltage(1, 1)
        value = value / 10
        #print('Value: ' + str(value))
        flow = value * self.fullrange / self.voltagespan
        return flow

    def set_flow(self, flow):
        """ Set the wanted flow (or pressure) """
        voltage = flow *  self.voltagespan / self.fullrange
        print('Voltage: ' + str(voltage))
        self.daq.set_dac_voltage(1, voltage)
        return voltage


class FlowControl(threading.Thread):
    """ Keep updated values of the current flow or pressure """
    def __init__(self, mfcs, name):
        threading.Thread.__init__(self)
        self.daemon = True
        self.mfcs = mfcs
        print(mfcs)
        devices = list(self.mfcs.keys())
        self.values = {}
        for device in devices:
            self.values[device] = None

        self.pullsocket = DateDataPullSocket(name + '_analog_control', devices,
                                             timeouts=[3.0] * len(devices))
        self.pullsocket.start()

        self.pushsocket = DataPushSocket(name + '_analog_pc_control', action='enqueue')
        self.pushsocket.start()

        self.livesocket = LiveSocket(name + '_analog_mfc_control', devices)
        self.livesocket.start()
        self.running = True

    def value(self, device):
        """ Return the current value of a device """
        return self.values[device]

    def run(self):
        while self.running:
            time.sleep(0.1)
            qsize = self.pushsocket.queue.qsize()
            while qsize > 0:
                print('queue-size: ' + str(qsize))
                element = self.pushsocket.queue.get()
                mfc = list(element.keys())[0]
                self.mfcs[mfc].set_flow(element[mfc])
                qsize = self.pushsocket.queue.qsize()

            for mfc in self.mfcs:
                flow = self.mfcs[mfc].read_flow()
                self.values[mfc] = flow
                print(flow)
                self.pullsocket.set_point_now(mfc, flow)
                self.livesocket.set_point_now(mfc, flow)
