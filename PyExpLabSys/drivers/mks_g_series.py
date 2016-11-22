import serial
import time
import logging

class Mks_G_Series():

    def __init__(self, port='/dev/ttyUSB0'):
        # TODO: Auto-check all possible baud-rates
        self.ser = serial.Serial(port, 9600)
        self.ser.parity = serial.PARITY_NONE
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.stopbits = serial.STOPBITS_ONE

    def checksum(self, command):
        """ Calculate checksum of command """
        com_string = '@' + command
        total = 0
        for i in range(0, len(com_string)):
            total = total + ord(com_string[i])
        return (hex(total)[-2:]).upper()

    def comm(self, command, addr):
        com_string = str(addr).zfill(3) + command + ';'
        checksum = self.checksum(com_string)
        com_string = '@@@@' + com_string + checksum
        self.ser.write(com_string)
        time.sleep(0.1)
        reply = self.ser.read(self.ser.inWaiting())
        if len(reply) == 0:
            logging.warn('No such device')
        else:
            if reply[-2:] == self.checksum(reply[1:-2]):
                reply = reply[6:-3] # Cut away master address and checksum
            else:
                logging.error('Checksum error in reply')
                reply = ''
            if reply[0:3] == 'ACK':
                reply = reply[3:]
            else:
                logging.warn('Error in command')
        return reply

    def read_full_scale_range(self, addr):
        command = 'U?'
        unit = self.comm(command, addr)
        command = 'FS?'
        value = self.comm(command, addr)
        return value + unit

    def read_device_address(self, address=254):
        command = 'CA?'
        return self.comm(command, address)

    def set_device_address(self, old_addr, new_addr):
        if (new_addr > 0) and (new_addr < 254):
            addr_string = str(new_addr).zfill(3)
            command = 'CA!' + addr_string
            self.comm(command, old_addr)

    def read_current_gas_type(self, addr):
        command = 'PG?'
        reply = self.comm(command, addr)
        return reply

    def read_run_hours(self, addr):
        """ Return number of running hours of mfc """
        command = 'RH?'
        return self.comm(command, addr)

    def read_setpoint(self, addr):
        """ Read the flow setpoint """
        command = 'SX?'
        value = float(self.comm(command, addr))
        return value

    def set_flow(self, value, addr=254):
        """ Set the flow setpoint """
        command = 'SX!' + str(round(value, 1))
        self.comm(command, addr)
        return True

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
    mks = Mks_G_Series()
    #print mks.read_run_hours(254)
    #print mks.set_device_address(254,005)
