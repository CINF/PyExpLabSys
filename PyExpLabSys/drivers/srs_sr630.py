import serial
import time

# Legal values for units
UNITS = ['ABS', 'CENT', 'FHRN', 'MDC', 'DC']

class SRS_SR630():
    """ Driver for Standford Research Systems, Model SR630 """

    def __init__(self, port):
        self.f = serial.Serial(port, 9600, timeout=2)
        time.sleep(0.1)

    def comm(self, command):
        """ Ensures correct protocol for instrument """
        endstring = '\r'
        self.f.write(command + endstring)
        if command.find('?') > -1:
            return_string = self.f.readline()[:-2]
        else:
            return_string = True
        return return_string

    def config_analog_channel(self, channel, follow_temperature=False, value=0):
        """ Configure an analog out channel """
        if (value < -10) or (value > 10):
            return False

        if follow_temperature:
            command = 'VMOD ' + str(channel) + ',0'
            self.comm(command)
        else:
            command = 'VMOD ' + str(channel) + ',1'
            self.comm(command)
            command = 'VOUT ' + str(channel) + ',' + str(value)
            self.comm(command)
        return True

    def set_unit(self, channel, unit):
        """ Set the measurement unit for a channel """
        if not unit in UNITS:
            return False
        command = 'UNIT ' + str(channel) + ',' + unit
        self.comm(command)
        time.sleep(0.2) # Need a bit of time to return correct unit
        return True

    def tc_types(self):
        """ List all configuration of all channels """
        types = {}
        command = 'TTYP? '
        for i in range(1,17):
            types[i] = self.comm(command + str(i))
        return types
    
    def read_open_status(self):
        """ Check for open output on all channels """
        for i in range(1, 17):
            self.read_channel(i)
        command = 'OPEN?'
        # TODO: Parse the output
        open_status = bin(int(self.comm(command)))
        return open_status

    def read_serial_number(self):
        """ Return the serial number of the device """
        return self.comm('*IDN?')

    
    def read_channel(self, ch):
        """ Read the actual value of a channel """
        command = 'CHAN?'
        current_channel = self.comm(command)
        if int(current_channel) ==  ch:
            command = 'MEAS? ' + str(ch)
            value = self.comm(command)
        else:
            command = 'CHAN ' + str(ch)
            self.comm(command)
            command = 'MEAS? ' + str(ch)
            value = self.comm(command)
        return value

if __name__ == '__main__':
    srs = SRS_SR630('/dev/ttyUSB0')
    print(srs.read_serial_number())
    print(str(srs.read_channel(2)))
    print(srs.set_unit(2, 'CENT'))
    print(str(srs.read_channel(2)))
    print(srs.read_open_status())
    print(srs.tc_types())
    print(srs.config_analog_channel(1, follow_temperature=False, value=0.2))
