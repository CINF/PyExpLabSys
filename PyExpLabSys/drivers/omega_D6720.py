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
        self.instrument.debug = False

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

    def read_address(self, new_address = None):
        """ Read the RS485 address of the device """
        old_address = self.comm(0)
        return(old_address)

    #def write_enable(self):
    #    self.comm(240, 2)
    #    time.sleep(0.8)
    #    return(True)

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
        if ch <0 or ch> 14:
            print('Channel no is outside range, should be between 0-14')
        else:
            reply = self.instrument.write_bit(ch, value, functioncode=5)
        return reply

if __name__ == '__main__':
    port = '/dev/serial/by-id/usb-FTDI_USB-RS485_Cable_FTYIWN2Q-if00-port0'
    omega = OmegaD6720(1, port=port)
    #print omega.instrument.read_register(0)
    #omega.instrument.write_bit(7, 1)
    #omega.instrument.write_bit(8, 1)
    #omega.instrument.write_bit(9, 1)
    #omega.instrument.write_bit(10, 1)
    for i in range(15):
        val= omega.instrument.write_bit(i, value=0)
        print 'i: ' + str(i) + '  , value: ' + str(val)
    
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
