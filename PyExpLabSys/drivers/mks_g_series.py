""" Driver for MKS g-series flow controller """
from __future__ import print_function
import time
import logging
import serial

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

NAK_TABLE = {
    '01': 'Checksum error',
    '10': 'Syntax error',
    '11': 'Data length error',
    '12': 'Invalid data',
    '13': 'Invalid operating mode',
    '14': 'Invalid action',
    '15': 'Invalid gas',
    '16': 'Invalid control mode',
    '17': 'Invalid command',
    '24': 'Calibration error',
    '25': 'Flow too large',
    '27': 'Too many gases in gas table',
    '28': 'Flow cal error, valve not open',
    '98': 'Internal device error',
    '99': 'Internal device error',
}


class MksGSeries:
    """ Driver for G-series flow controllers from MKS """

    def __init__(self, port='/dev/ttyUSB0'):
        # TODO: Auto-check all possible baud-rates
        self.ser = serial.Serial(port, 9600)
        self.ser.parity = serial.PARITY_NONE
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.stopbits = serial.STOPBITS_ONE

    def checksum(self, command):
        """ Calculate checksum of command """
        com_string = '@' + command
        checksum = sum([ord(i) for i in com_string])
        # The following hack deviates from the manual, but has proven to work on two different setups
        if 'NAK' in com_string:
            checksum += 9
        return hex(checksum)[-2:].upper()

    def comm(self, command, addr):
        """ Implements communication protocol """
        # TODO: add retries on comm errors
        com_string = str(addr).zfill(3) + command + ';'
        checksum = self.checksum(com_string)
        com_string = '@@@' + com_string + checksum
        com_string = com_string.encode('ascii')
        self.ser.write(com_string)
        time.sleep(0.1)
        raw_reply = self.ser.read(self.ser.inWaiting())
        # In case that noise adds zeros on either side:
        reply = raw_reply.strip(b'\x00')
        reply = reply.decode('ascii')
        if len(reply) == 0:
            LOGGER.warning('No such device')
            return ''
        # Response structure: '@@@000' + 'ACK' + content + ';' + 2-char-checksum
        noise_check_passed = reply.find(';') == len(reply) - 3
        ack = reply[6:9]
        content = reply[9:-3]
        crc = reply[-2:]
        if noise_check_passed:
            # Calculate checksum (the first @ is added again during calc)
            if crc == self.checksum(reply[1:-2]):
                if ack == 'ACK':
                    return content
                elif ack == 'NAK':
                    message = NAK_TABLE[content]
                    print('NAK error {} in command: {}'.format(content, message))
                    LOGGER.warning(
                        'NAK error {} in command: {}'.format(content, message)
                    )
                    return ''
                else:
                    LOGGER.warning('Unexpected response: {}'.format(repr(raw_reply)))
                    return ''
            else:
                LOGGER.error('Checksum error in reply')
                return ''
        else:
            LOGGER.warning('Response seemingly too noisy: {}'.format(repr(raw_reply)))
            return ''

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

    def read_internal_temperature(self, addr=254):
        """ Return the internal temperature in degrees Celcius """
        command = 'TA?'
        return self.comm(command, addr)


if __name__ == '__main__':
    MKS = MksGSeries()
    print(MKS.read_serial_number(1))
    print(MKS.read_full_scale_range(1))
    # print(MKS.set_device_address(254, 005))
