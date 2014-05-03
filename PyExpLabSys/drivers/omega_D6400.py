import minimalmodbus
import time
import logging

class OmegaD6400():
    def __init__(self, address=1, port='/dev/ttyUSB1'):
        self.instrument = minimalmodbus.Instrument(port, address) 
        self.instrument.serial.baudrate = 9600
        self.ranges = [0] * 7
        for i in range(0,7):
            self.ranges[i] = {}
            self.ranges[i]['action'] = 'disable'
            self.ranges[i]['fullrange'] = '0'
        self.ranges[0]['action'] = 'voltage'
        self.ranges[0]['fullrange'] = '10'

        for i in range(0,7):
            print i
            self.ranges[i]['fullrange']
            self.ranges[i]['action']
            self.update_range_and_function(i, fullrange=self.ranges[i]['fullrange'], action=self.ranges[i]['action'])

    def comm(self, command, value=None):
        reply = None
        error = True

        while error is True:
            try:
                if value == None:
                    reply = self.instrument.read_register(command)
                else:
                    self.instrument.write_register(command, value)
                error = False
            except ValueError:
                logging.warn('D6400 driver: Value Error')
                self.instrument.serial.read(self.instrument.serial.inWaiting())
                time.sleep(0.5)
            except IOError:
                logging.warn('D6400 driver: IOError')
                error = True
                time.sleep(0.1)
        return reply

    #To be deleted
    def read_voltage(self, channel):
        reply = self.comm(48+channel)
        if self.ranges[channel]['action'] == 'voltage':
            num_value =  reply - 2**15
            scale = 1.0 * 2**15 / float(self.ranges[channel]['fullrange'])
            value = num_value / scale
        else:
            value = None
        return(value)

    def read_value(self, channel):
        value = None
        reply = self.comm(48+channel)
        if self.ranges[channel]['action'] == 'voltage':
            num_value =  reply - 2**15
            scale = 1.0 * 2**15 / float(self.ranges[channel]['fullrange'])
            value = num_value / scale
        if self.ranges[channel]['action'] == 'tc':
            scale = 1.0 * 2**16 / 1400
            value = (reply/scale) - 150
        return(value)


    def write_enable(self):
        self.comm(240, 2)
        time.sleep(0.4)
        return(True)

    def range_codes(self, fullrange=0, action=None):
        """ Returns the code corresponding to a given range
        """
        codes = {}
        codes['tc'] = {}
        codes['tc']['J'] = 21
        codes['tc']['K'] = 34
        codes['tc']['T'] = 23
        codes['tc']['E'] = 24
        codes['tc']['R'] = 25
        codes['tc']['S'] = 26
        codes['tc']['B'] = 27
        codes['tc']['C'] = 28
        codes['voltage'] = {}
        codes['voltage']['10'] = 1
        codes['voltage']['5']  = 2
        codes['voltage']['1']  = 3
        codes['voltage']['0.1'] = 4
        codes['voltage']['0.05'] = 5
        codes['voltage']['0.025'] = 6
        codes['disable'] = 0
        codes['current'] = 3

        if action in ('tc', 'voltage'):
            code = codes[action][fullrange]
        if action in ('disable', 'current'):
            code = codes[action]
        return(code)

    def update_range_and_function(self, channel, fullrange=None, action=None):
        if not (action == None):
            self.write_enable()
            code = self.range_codes(fullrange, action)
            self.comm(96+channel, code)
            time.sleep(0.1)
            self.ranges[channel]['action'] = action
            self.ranges[channel]['fullrange'] = fullrange
        return(self.comm(96+channel))

if __name__ == '__main__':
    omega = OmegaD6400(1)

    omega.update_range_and_function(0, action=None)

    omega.update_range_and_function(0, action='voltage', fullrange='5')
    omega.update_range_and_function(5, action='voltage', fullrange='0.1')
    omega.update_range_and_function(6, action='voltage', fullrange='0.1')
    print omega.read_voltage(5)
    print omega.read_voltage(6)
    #omega.update_range_and_function(5, action='voltage', fullrange='0.025')
    #omega.update_range_and_function(5, action='voltage', fullrange='0.025')
    #print omega.read_voltage(5)
    #print omega.read_voltage(6)
    omega.update_range_and_function(5, action='tc', fullrange='K')
    omega.update_range_and_function(6, action='tc', fullrange='K')

    time.sleep(1)
    print omega.read_voltage(0)
    for i in range(0,5000):
        print omega.read_value(5)
        print omega.read_value(6)

    """
    print omega.read_voltage(1)
    print omega.read_voltage(2)
    print omega.read_voltage(3)
    print omega.read_voltage(4)
    print omega.read_voltage(5)
    print omega.read_voltage(6)
    """
