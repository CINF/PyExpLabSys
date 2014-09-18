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
        time.sleep(0.5)
        reply = self.ser.read(self.ser.inWaiting())
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
        command = 'RH?'
        return self.comm(command, addr)

    def read_setpoint(self, addr):
        command = 'SX?'
        value = float(self.comm(command, addr))
        return value

    def set_setpoint(self, value, addr):
        command = 'SX!' + str(round(value,1))
        self.comm(command, addr)
        return(True)

    def read_flow(self, addr):
        command = 'FX?'
        return float(self.comm(command, addr))

    def read_serial_number(self, addr):
        command = 'SN?'
        return self.comm(command, addr)

mks = Mks_G_Series()
#print mks.read_serial_number(1)
#print mks.set_setpoint(2.2, 1)
#print mks.read_setpoint(1)
#print mks.read_flow(1)
#print mks.read_current_gas_type(1)
#print mks.read_device_address(2)
print mks.read_full_scale_range(2)


#print mks.read_run_hours(254)
#print mks.set_device_address(254,2)




"""
f = serial.Serial('/dev/ttyUSB0', 9600)

f.write('@@@@254WK!ON;FF')
time.sleep(0.5)
print f.inWaiting()
s = f.read(f.inWaiting())
print s
print '------'

f.write('@@@@254CA?;D9')
time.sleep(0.5)
print f.inWaiting()
s = f.read(f.inWaiting())
print s
print '-------'
f.write('@@@@254CA?;FF')
time.sleep(0.5)
print f.inWaiting()
s = f.read(f.inWaiting())
print s
print '-----'

"""
