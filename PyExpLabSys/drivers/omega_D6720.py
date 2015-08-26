# pylint: disable=C0301,R0904, C0103
import minimalmodbus
import time
import logging


class OmegaD6720(object):
    """ Driver for the Omega Instrument D6720 Digital Outputs """
    def __init__(self, address=1, port='/dev/ttyUSB0'):
        self.instrument = minimalmodbus.Instrument(port, address)
        self.instrument.serial.baudrate = 9600
        self.instrument.serial.timeout = 1.0  # Default setting leads to comm-errors
        self.instrument.debug = True
        #print self.instrument.serial
        #self.ranges = [0] * 8
        #for i in range(1, 8):
        #    self.ranges[i] = {}
        #    self.ranges[i]['action'] = 'disable'
        #    self.ranges[i]['fullrange'] = '0'
        #self.ranges[1]['action'] = 'voltage'
        #self.ranges[1]['fullrange'] = '10'
        #
        #for i in range(1, 8):
        #    print i
        #    self.update_range_and_function(i, fullrange=self.ranges[i]['fullrange'], action=self.ranges[i]['action'])
        #    print '!'

    def comm(self, command, value=None):
        """ Communicates with the device """
        reply = None
        error = True

        while error is True:
            print('COM: ' + str(command))
            try:
                if value is None:
                    reply = self.instrument.read_register(command)
                    print('RE: ' + str(reply))
                else:
                    reply = self.instrument.write_register(command, value)
                    print('RE: ' + str(reply))
                error = False
            except ValueError:
                logging.warn('D6720 driver: Value Error')
                replyER = self.instrument.serial.read(self.instrument.serial.inWaiting())
                print('RE error: ' + str(replyER))
                time.sleep(0.1)
                error = True
            except IOError:
                logging.warn('D6720 driver: IOError')
                replyER = self.instrument.serial.read(self.instrument.serial.inWaiting())
                print('RE error: ' + str(replyER))
                error = True
                time.sleep(0.1)
        return reply

    #def read_value(self, channel):
    #    """ Read a measurement value from a channel """
    #    value = None
    #    reply = self.comm(47 + channel)
    #    if self.ranges[channel]['action'] == 'voltage':
    #        num_value = reply - 2 ** 15
    #        scale = 1.0 * 2 ** 15 / float(self.ranges[channel]['fullrange'])
    #        value = num_value / scale
    #    if self.ranges[channel]['action'] == 'tc':
    #        scale = 1.0 * 2 ** 16 / 1400
    #        value = (reply/scale) - 150
    #    return(value)

    def read_address(self, new_address = None):
        """ Read the RS485 address of the device """
        old_address = self.comm(0)
        return(old_address)


    def write_enable(self):
        self.comm(240, 2)
        time.sleep(0.8)
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
        codes['voltage']['5'] = 2
        codes['voltage']['1'] = 3
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
        if not action is None:
            self.write_enable()
            code = self.range_codes(fullrange, action)
            self.comm(95 + channel, code)
            print '##'
            time.sleep(0.1)
            self.ranges[channel]['action'] = action
            self.ranges[channel]['fullrange'] = fullrange
        return(self.comm(95 + channel))

    def read_value(self,):
        reply = self.instrument.read_register(5)
        #reply = self.instrument.write_register(5+, )
        print(reply)
        #self.comm(2)

if __name__ == '__main__':
    port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTYIWN2Q-if00-port0'
    omega = OmegaD6720(1, port=port)
    omega.read_value()
    #omega.comm(40033)
    #omega.comm(04)
    #omega.comm(05, value=0)
    #omega.comm(04)

    """
    omega.update_range_and_function(1, action='voltage', fullrange='10')
    omega.update_range_and_function(2, action='voltage', fullrange='10')
    omega.update_range_and_function(3, action='voltage', fullrange='10')
    omega.update_range_and_function(4, action='voltage', fullrange='10')
    omega.update_range_and_function(5, action='voltage', fullrange='10')
    omega.update_range_and_function(6, action='voltage', fullrange='10')
    omega.update_range_and_function(7, action='voltage', fullrange='10')
    for klaf in range(0, 100):
        print omega.read_value(1)
        print omega.read_value(2)
        print omega.read_value(3)
        print omega.read_value(4)
        print omega.read_value(5)
        print omega.read_value(6)
        print omega.read_value(7)
        print '--------------'
        time.sleep(2)
    """
    #omega.update_range_and_function(1, action='tc', fullrange='K')
    #omega.update_range_and_function(2, action='tc', fullrange='K')
    #omega.update_range_and_function(3, action='tc', fullrange='K')
    #omega.update_range_and_function(4, action='tc', fullrange='K')
    #omega.update_range_and_function(5, action='tc', fullrange='K')
    #omega.update_range_and_function(6, action='tc', fullrange='K')
    #omega.update_range_and_function(7, action='tc', fullrange='K')
    #print omega.read_value(1)
    #print omega.read_value(2)
    #print omega.read_value(3)
    #print omega.read_value(4)
    #print omega.read_value(5)
    #print omega.read_value(6)
    #print omega.read_value(7)
