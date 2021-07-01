import serial
import time
import datetime
import logging
import threading
import numpy as np
from queue import Empty
#from scipy.signal import savgol_filter

from PyExpLabSys.common.sockets import DateDataPullSocket, DataPushSocket

logging.basicConfig(filename='DI2008.log', level=logging.WARNING)
LOGGER = logging.getLogger(__name__)

CODENAME = 'omicron_T_sample'

class DI2008(object):

    def __init__(self, port='/dev/ttyACM0'):
        self.port = port
        self.baudrate = 115200
        self.timeout = 0.1
        self.ser = serial.Serial(port=self.port,
                                 baudrate=self.baudrate,
                                 timeout=self.timeout,
        )
        self.acquiring = False
        self.stop()
        self.ps = None
        self.packet_size(3)
        self.config_scan_list()
        self.decimal(1)
        self.srate(4)
        print('DI 2008 initialized')
        self.get_sample_rate()
        self.tc = {'B': [0.023956, 1035],
                   'E': [0.018311, 400],
                   'J': [0.021515, 495],
                   'K': [0.023987, 586],
                   'N': [0.022888, 550],
                   'R': [0.02774, 859],
                   'S': [0.02774, 859],
                   'T': [0.009155, 100]
        }


    def comm(self, command, timeout=1, echo=True):
        prev = self.ser.read(self.ser.inWaiting())
        if echo:
            print('Flushing: ' + repr(prev))
        self.ser.write((command+'\r').encode())
        # If not acquiring, read reply from DI2008
        if not self.acquiring:
            time.sleep(.1)
            # Echo commands if not acquiring
            t0 = time.time()
            while True:
                if time.time() - t0 > timeout:
                    return 'Timeout'
                if self.ser.inWaiting() > 0:
                    while True:
                        try:
                            s = self.ser.readline().decode()
                            s = s.strip('\n')
                            s = s.strip('\r')
                            s = s.strip(chr(0))
                            if echo:
                                print(repr(s))
                            break
                        except:
                            continue
                    if s != "":
                        if echo:
                            print(s)
                        return s.lstrip(command).strip()

    def config_scan_list(self):
        """FIXME
        Configure channels"""
        self.comm('slist 0 4864') # K-type TC on channel 0

    def start(self, echo=True):
        self.acquiring = True
        self.comm('start', echo=echo)

    def stop(self, echo=True):
        #self.ser.write('stop\r'.encode())
        self.acquiring = False
        #time.sleep(1)
        self.comm('stop', echo=echo)


    def packet_size(self, value):
        if value not in range(4):
            raise ValueError('Value must be 0, 1, 2, or 3.')
        psdict = {0: 16, 1: 32, 2: 64, 3: 128}
        self.ps = psdict[value] # Packet size [bytes]
        print('Packet size: {} B'.format(self.ps))
        self.comm('ps ' + str(value))

    def get_sample_rate(self):
        srate = int(self.comm('info 9'))
        self.sample_rate = srate / (self.sr * self.dec)
        print('Sample rate: ', self.sample_rate, ' Hz')

    def set_sample_rate(self):
        pass #NOTIMPLEMENTED

    def decimal(self, value):
        value = int(value)
        if value >= 1 and value <= 32767:
            self.comm('dec ' + str(value))
            self.dec = value
        else:
            raise ValueError('Value DEC out of range')

    def srate(self, value):
        value = int(value)
        if value >= 4 and value <= 2232:
            self.comm('srate ' + str(value))
            self.sr = value
        else:
            raise ValueError('Value SRATE out of range')

    def read_TC(self, tc_type, timeout=0.1):
        """Read a thermocouple byte"""
        
        t0 = time.time()
        temp = 0
        values = int(self.ps/2)
        value_list = np.ones(values)
        error = 0
        for i in range(values):
            #if False:
            #    while True:
            #        if time.time() - t0 > timeout:
            #            print('TC Timeout')
            #            return t0, None
            #        try:
            #            n = self.ser.inWaiting() == 0
            #        except OSError:
            #            n = 0
            #        if n > 0:
            #            break
            #        time.sleep(1./self.sample_rate/20*self.ps)
            #else:
            #    while self.ser.inWaiting() == 0:
            #        time.sleep(1./self.sample_rate/20*self.ps)
            #
            byte = None
            while byte is None:
                try:
                    byte = self.ser.read(2)
                    error = 0
                except serial.serialutil.SerialException:
                    error += 1
                    print(error)
                    if error > 3:
                        try:
                            self.ser.close()
                            self.ser = serial.Serial(port=self.port,
                                                     baudrate=self.baudrate,
                                                     timeout=self.timeout,
                            )
                        except serial.serialutil.SerialException:
                            pass
                    if error > 10:
                        print('Error count in reading TC: {}'.format(error))
                        raise
                    time.sleep(0.15)
                    LOGGER.warning('{}: SerialException'.format(datetime.datetime.now()))
                    continue
            else:
                value_list[i] = int.from_bytes(byte, byteorder='little', signed=True)
        for result in value_list:
            if result == 32767:
                result = 'cjc error'
                break
            elif result == -32768 or result == -32760:
                result = 'open'
                break
            else:
                try:
                    param = self.tc[tc_type]
                except KeyError:
                    raise ValueError('tc_type must be a valid thermocouple type!')
                temp += param[0] * result + param[1]
        temp /= values
        if not isinstance(result, str):
            return t0, temp
        else:
            return t0, result


class Reader(threading.Thread):

    def __init__(self, driver, pullsocket, pushsocket,
                 window=53, order=1, tstop=4, deltat=None):
        threading.Thread.__init__(self)
        self.daemon = False
        self.dev = driver
        self.pullsocket = pullsocket
        self.pushsocket = pushsocket
        self.size = 200
        self.x, self.y = np.zeros(self.size), np.zeros(self.size)
        self.y_filter = np.zeros(self.size)
        self.window = window
        self.order = order
        self.t_stop = tstop
        self.res = None
        self.public = None
        self.quit = False
        self.measure = False
        print('Reader initialized')

    def update_data(self):
        self.x[:-1], self.y[:-1] = self.x[1:], self.y[1:]
        self.res = self.dev.read_TC('K')
        if isinstance(self.res[1], str):
            self.x[-1] = self.res[0]
            #self.public = None
            if self.res[1] == 'open':
                self.public = -1000
            elif self.res[1] == 'cjc error':
                self.public = -2000
            else:
                self.public = None
        else:
            self.x[-1], self.y[-1] = self.res
            self.y_filter = savgol_filter(self.y, self.window, self.order)
            self.public = self.y_filter[-3]
        self.pullsocket.set_point_now(CODENAME, self.public)


    def print_state(self):
        string = '{:15.7} s         '
        string += '{}                     ' if isinstance(self.res[1], str) else '{:8.5} C             '
        string += '{}          ' if self.public < 0 or self.public is None else '{:8.5} C      '
        try:
            print(string.format(self.res[0] - self.t0, self.res[1], self.public), end='\r')
        except ValueError:
            print(self.res, self.public, end='\r')

    def run(self, stop=4):
        print('Starting while loop - quit with KeyboardInterrupt (Ctrl+C)')
        print('\n' + ' '*10 + 'Time' + ' '*10 + 'Temperature (raw)' + ' '*5 + 'Temperature (Savgol filter)')
        first_msg = True
        msg = 'Ready to start scanning on external signal..'
        while self.quit is False:
            if first_msg is True:
                first_msg = False
                print(msg.ljust(79), end='\r')
            time.sleep(0.5)
            if self.measure is True:
                self.t0 = time.time()
                self.dev.start(echo=False)
                while self.measure is True:
                    try:
                        self.update_data()
                    except ValueError:
                        print('ValueError')
                        continue
                    
                    
                    self.print_state()

                    # Stop criteria
                    if self.t_stop > 0:
                        if self.x[-1] - self.t0 > self.t_stop:
                            self.quit = True
                else:
                    self.dev.stop(echo=False)
                    first_msg = True



if __name__ == '__main__':
    #path = '/dev/ttyACM0'
    path = '/dev/serial/by-id/usb-DATAQ_Instruments_Generic_Bulk_Device_00000000_DI-2008-if00'
    dev = DI2008(port=path)
    #dev.comm('ps 0')
    #dev.initialize()

    pullsocket = DateDataPullSocket('omicron_TPD_sample_temp',
                                    [CODENAME],
                                    #timeouts=1,
                                    port=9002,
    )
    pullsocket.start()

    pushsocket = DataPushSocket('omicron_DI2008_pushsocket', port=8500,
                                action='enqueue', return_format='raw',
    )
    pushsocket.start()
    
    
    time.sleep(1)
    reader = Reader(dev, pullsocket, pushsocket, window=53, order=1)
    reader.t_stop = -1
    #window, order = 53, 1
    ifdone = False
    reader.start()
    time.sleep(0.1)


    #try:
    #    element = self.pushsocket.queue.get(timeout=1)
    #    print(element['cmd'])
    #except Empty:
    #    pass
    #if self.running is True:
    #    break

    while True:
        if not reader.isAlive():
            break
        try:
            element = pushsocket.queue.get(timeout=1)
            cmd = element['cmd']
            if cmd == 'start':
                reader.measure = True
            elif cmd == 'stop':
                reader.measure = False
        except Empty:
            pass
        except KeyboardInterrupt:
            reader.measure = False
            reader.quit = True
            break

