""" Driver for ISO-TECH IPS power supply series

It has not been possible to get the device to give any
meaningfull replys, but actually setting output values
works.
"""
import serial
import time

class IPS(object):
    """ Driver for IPS power supply """
    def __init__(self, port):
        self.serial = serial.Serial(port, 2400, timeout=10, xonxoff=False,
                                    rtscts=False)

    def comm(self, command):
        """ Communicate with instrument """
        self.serial.write(command + '\r')
        # The unit will fail to run at more than 2Hz
        time.sleep(0.5)
        return True

IPS = IPS('/dev/ttyS0')


