
""" Driver for MKS g-series flow controller """
from __future__ import print_function
import time
import logging
import serial
from PyExpLabSys.common.supported_versions import python2_and_3
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())
python2_and_3(__file__)

class MksGSeries():
    """ Driver for G-series flow controllers from MKS """
    def __init__(self, port='/dev/ttyUSB0'):
        # TODO: Auto-check all possible baud-rates
        self.ser = serial.Serial(port, 9600)
        self.ser.parity = serial.PARITY_NONE
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.stopbits = serial.STOPBITS_ONE

    def checksum(self, command, reply=False):
        """ Calculate checksum of command """
        if not reply:
            com_string = '@' + command
        else:
            com_string = command
        total = 0
        for i in range(0, len(com_string)):
            total = total + ord(com_string[i])
        return (hex(total)[-2:]).upper()

    def comm(self, command, addr):
        """ Implements communication protocol """
        com_string = str(addr).zfill(3) + command + ';'
        checksum = self.checksum(com_string)
        com_string = '@@@@' + com_string + checksum
        com_string = com_string.encode('ascii')
        self.ser.write(com_string)
        time.sleep(0.1)
        reply = self.ser.read(self.ser.inWaiting())
        try:
            reply = reply.decode('ascii')
        except: UnicodeDecodeError:
            reply = reply.decode('ascii', 'ignore')
            reply = reply.strip('\x00')
            reply = '@' + reply

        if len(reply) == 0:
            LOGGER.warning('No such device')
        else:
            if reply[-3:] == self.checksum(reply[1:-3], reply=True):
                reply = reply[6:-3] # Cut away master address and checksum
            else:
                LOGGER.error('Checksum error in reply')
                reply = ''
            if reply[1:4] == 'ACK':
                reply = reply[4:-3]
            else:
                LOGGER.warning('Error in command')
        return reply

    def read_full_scale_range(self, addr):
        """ Read back the current full scale range from the instrument """
        command = 'U?'
        unit = self.comm(command, addr)
        command = 'FS?'
        value = self.comm(command, addr)
        return value + unit

    def read_device_address(self, address=254):
        """ Read the device address """
        command = 'CA?'
        return self.comm(command, address)

    def set_device_address(self, old_addr, new_addr):
        """ Set the device address """
        if (new_addr > 0) and (new_addr < 254):
            addr_string = str(new_addr).zfill(3)
            command = 'CA!' + addr_string
            self.comm(command, old_addr)

    def read_current_gas_type(self, addr):
        """ Read the current default gas type """
        command = 'PG?'
        reply = self.comm(command, addr)
        return reply

    def read_run_hours(self, addr):
        """ Return number of running hours of mfc """
        command = 'RH?'
        return self.comm(command, addr)

    def read_setpoint(self, addr):
        """ Read current setpoint """
        command = 'SX?'
        value = float(self.comm(command, addr))
        return value

    def set_flow(self, value, addr=254):
        """ Set the flow setpoint """
        command = 'SX!' + str(round(value, 1))
        self.comm(command, addr)
        return True

    def purge(self, t=1, addr=254):
        """ purge for t seconds, default is 1 second """
        command1 = 'VO!PURGE'
        command2 = 'VO!NORMAL'
        self.comm(command1, addr)
        print('PURGING')
        time.sleep(abs(t))
        self.comm(command2, addr)
        print('DONE PURGING')

    def read_flow(self, addr=254):
        """ Read the flow """
        command = 'FX?'
        error = 1
        while (error > 0) and (error < 50):
            try:
                flow = float(self.comm(command, addr))
                error = -1
            except ValueError:
                error = error + 1
                flow = -1
        return flow

    def read_serial_number(self, addr=254):
        """ Read the serial number of the device """
        command = 'SN?'
        return self.comm(command, addr)

if __name__ == '__main__':
    MKS = MksGSeries()
    print(MKS.read_serial_number(1))
    print(MKS.read_full_scale_range(1))
#print(MKS.set_device_address(254,005))
