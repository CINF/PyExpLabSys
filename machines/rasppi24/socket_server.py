""" Flow controller for microreactor Bronkhorst devices """
from __future__ import print_function
import threading
import time
import PyExpLabSys.drivers.bronkhorst as bronkhorst
from PyExpLabSys.common.database_saver import ContinuousDataSaver
from PyExpLabSys.common.value_logger import ValueLogger
from PyExpLabSys.common.sockets import DateDataPullSocket
from PyExpLabSys.common.sockets import DataPushSocket
from PyExpLabSys.common.sockets import LiveSocket
from PyExpLabSys.common.supported_versions import python2_and_3
import credentials
python2_and_3(__file__)

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

    def value(self, channel):
        """ Helper function for the reactor logger functionality """
        if channel == 1:
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
                if mfc == 'M11213502A':
                    flow = flow * 1000
                #print(mfc + ': ' + str(flow))
                self.pullsocket.set_point_now(mfc, flow)
                self.livesocket.set_point_now(mfc, flow)
                if mfc == 'M13201551A':
                    print("Pressure: " + str(flow))
                    self.reactor_pressure = flow

def main():
    """ Main function """
    devices = ['M13201551A', 'M11200362F', 'M8203814A', 'M8203814B',
               'M11200362B', 'M11213502A']
    ranges = {}
    ranges['M13201551A'] = 5 # Microreactor, pressure controller
    ranges['M11200362F'] = 1 # Microreactor, flow 2
    ranges['M8203814A'] = 10 # flow 5 (argon calibrated)
    ranges['M8203814B'] = 3 # Microreactor, flow 1 (argon calibrated)
    ranges['M11200362B'] = 10 # Palle Flow
    ranges['M11213502A'] = 2.5 # Palle pressure

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

    datasocket = DateDataPullSocket('microreactor_mfc_control',
                                    devices,
                                    timeouts=[3.0, 3.0, 3.0, 3.0, 3.0, 3.0],
                                    port=9000)
    datasocket.start()

    pushsocket = DataPushSocket('microreactor_mfc_control', action='enqueue')
    pushsocket.start()
    livesocket = LiveSocket('microreactor_mfc_control', devices)
    livesocket.start()

    flow_control = FlowControl(mfcs, datasocket, pushsocket, livesocket)
    flow_control.start()

    logger = ValueLogger(flow_control, comp_val=1, comp_type='log', low_comp=0.0001,
                         channel=1)
    logger.start()

    db_logger = ContinuousDataSaver(continuous_data_table='dateplots_microreactor',
                                    username=credentials.user,
                                    password=credentials.passwd,
                                    measurement_codenames=['mr_reactor_pressure'])
    db_logger.start()

    time.sleep(5)
    while True:
        time.sleep(0.25)
        value = logger.read_value()
        if logger.read_trigged():
            print(value)
            db_logger.save_point_now('mr_reactor_pressure', value)
            logger.clear_trigged()


if __name__ == '__main__':
    main()
