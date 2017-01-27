# pylint: disable=C0301,R0904, C0103
import minimalmodbus
import time
#import logging


class OmegaD6000(object):
    """ Driver for the Omega Instrument D6720 Digital Outputs """
    def __init__(self, address=1, port='/dev/ttyUSB0'):
        self.instrument = minimalmodbus.Instrument(port, address)
        self.instrument.serial.baudrate = 9600
        self.instrument.serial.timeout = 1.0  # Default setting leads to comm-errors
        self.instrument.debug = False

    def comm(self, command, value=None):
        """ Communicates with the device """
        reply = None
        error = True
        count = 0

        while error is True and count < 10:
            count += 1
            #print('COM: ' + str(command))
            try:
                if value is None:
                    reply = self.instrument.read_register(command)
                    #print('RE: ', reply)
                else:
                    reply = self.instrument.write_register(command, value)
                    #print('REv: ', reply)
                error = False
            except ValueError:
                #logging.warn('D6720 driver: Value Error')
                replyER = self.instrument.serial.read(self.instrument.serial.inWaiting())
                print('RE ValueError: ' + str(replyER))
                time.sleep(0.1)
                error = True
            #except IOError:
            #    #logging.warn('D6720 driver: IOError')
            #    replyER = self.instrument.serial.read(self.instrument.serial.inWaiting())
            #    print('RE IOError: ', str(replyER), command, str(value))
            #    error = True
            #    time.sleep(0.1)
        return reply

    def read_address(self, new_address = None):
        """ Read the RS485 address of the device """
        old_address = self.comm(0)
        if new_address == None:
            old_address = self.comm(0)
        else:
            old_address = self.comm(0, int(new_address))
        return(old_address)

    def write_enable(self, enable = False):
        if enable == False:
            self.comm(40241 - 40001, 0)
        elif enable == True:
            self.comm(40241 - 40001, 2)
        time.sleep(0.8)
        return(True)
        
    def write_initialvalues(self, valuelist = None):
        """ set the timer of the watchdog """
        if type(valuelist) == type([]):
            V = 0
            for i, f in enumerate(valuelist):
                V += f * (2**i)
            self.write_enable(enable = True)
            self.comm(40097-40001, int(V))
            self.write_enable(enable = False)

    def write_watchdogtimer(self, settime = None):
        """ set the timer of the watchdog """
        if not settime == None:
            self.write_enable(enable = True)
            self.comm(40096-40001, int(settime))
            self.write_enable(enable = False)
            
    def read_watchdogtimer(self, settime = None):
        """ set the timer of the watchdog """
        re = self.comm(40096-40001)
        return re

    def close(self):
        """Close the connection to the device"""
        #LOGGER.debug('Driver asked to close')
        self.instrument.serial.close()
        #LOGGER.info('Driver closed')
        
class OmegaD6500(OmegaD6000):
    def __init__(self, address=1, port='/dev/ttyUSB0', activechannel = None):
        OmegaD6000.__init__(self, address=address, port=port)
        self.active_ch = activechannel
    def set_channel(self, ch, value):
        ivalue = int(float(value) * 0xffff/10.)
        self.comm(40048 + int(ch) - 40001, ivalue)
        
    def get_channel(self, ch):
        return self.comm(40096 + int(ch) - 40001)
        
    def set_channel_one(self, value):
        ivalue = int(float(value) * 0xffff/10.)
        self.set_channel(ch=1, value=ivalue)
        
    def set_channel_two(self, value):
        ivalue = int(float(value) * 0xffff/10.)
        self.set_channel(ch=2, value=ivalue)
        
    def set_value(self, value):
        if self.active_ch == 1 or self.active_ch == 2:
            self.set_channel(self.active_ch, value)
            #print(self.get_value())
        
    def get_channel_one(self):
        return self.get_channel(ch=1)
        
    def get_channel_two(self):
        return self.get_channel(ch=2)
    
    def get_value(self):
        if self.active_ch == 1 or self.active_ch == 2:
            return self.get_channel(self.active_ch)
            #print(v)
    
    
class OmegaD6720(OmegaD6000):
    def __init__(self, address=1, port='/dev/ttyUSB0'):
        OmegaD6000.__init__(self, address=address, port=port)
    def read_channel(self, ch=0):
        """ Read status of channel i"""
        reply = None
        if ch < 0 or ch > 14:
            print('Channel no is outside range, should be between 0-14')
        else:
            reply = self.instrument.read_bit(ch, functioncode=1)
        return reply
    
    def write_channel(self,ch=0, value=0):
        """ Set channel to value 0 or 1"""
        reply =None
        if ch < 0 or ch > 14:
            print('Channel no is outside range, should be between 0-14')
        else:
            reply = self.instrument.write_bit(ch, value, functioncode=5)
        time.sleep(0.17)
        return reply

    def all_off(self):
        """ Set channel to value 0 or 1"""
        reply = None
        for i in range(15):
            val= self.write_channel(ch=i, value=0)
            print 'i: ' + str(i) + '  , value: ' + str(val)
        return reply


if __name__ == '__main__':
    port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTYIWN2Q-if00-port0'
    omega1 = OmegaD6500(2, port=port, activechannel=1)
    omega2 = OmegaD6500(2, port=port, activechannel=2)
    omega3 = OmegaD6500(3, port=port, activechannel=1)
    omega4 = OmegaD6500(3, port=port, activechannel=2)
    print(omega1.get_value())
    print(omega2.get_value())
    print(omega3.get_value())
    print(omega4.get_value())
    #omega.read_address()
    #print omega.instrument.read_register(0)
    #omega.instrument.write_bit(7, 1)
    #omega.instrument.write_bit(8, 1)
    #omega.instrument.write_bit(9, 1)
    #omega.instrument.write_bit(10, 1)
    #for i in [0, 1, 2]:#range(15):
    #    time.sleep(2)
    #    val = omega.write_channel(ch=i, value=1)
    #    print 'i: ' + str(i) + '  , value: ' + str(val)
    #time.sleep(10)
    #omega.all_off()
    
    #print omega.instrument.write_register(240, 2)
    #print omega.instrument.write_register(96,0)
    #i = 1
    #time.sleep(1)
    #omega.read_channel(ch=i)
    #omega.write_channel(ch=i, value = 1)
    #time.sleep(3)
    #omega.read_channel(ch=i)
    #omega.write_channel(ch=i, value = 0)
            
    
    #omega.comm(40033)
    #omega.comm(04)
    #omega.comm(05, value=0)
    #omega.comm(04)
