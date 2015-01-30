import telnetlib
import time

from scpi import SCPI


class InterfaceOutOfBoundsError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Keithley2700(SCPI):
    """
    http://www.keithley.com/data?asset=10642
    """
    def __init__(self, interface = 'serial', hostname='', device='', tcp_port=0):
        if interface == 'lan':
            SCPI.__init__(self, 'lan', tcp_port=tcp_port, hostname=hostname)
        if interface == 'serial':
            SCPI.__init__(self, 'serial', device=device)
        #if not (output == 1 or output == 2):
        #    raise InterfaceOutOfBoundsError(output)
        #else:
        #    self.output = str(output)

    def read_voltage(self):
        """Reads the actual output voltage"""
        function_string = 'MEASURE:VOLT:DC?'
        value_string = self.scpi_comm(function_string)
        #value_string = '-2.01954693E-03VDC,+8816.272SECS,+62019RDNG#\r'
        
        try:
            value_split = value_string.split(',')
            value = float(value_split[0][:-3])
        except ValueError:
            value = -999999
        return(value, value_string)

    def read_resistance(self,):
        """Reads the actual output voltage"""
        function_string = 'MEASURE:RES?'
        value_string = self.scpi_comm(function_string)
        #try:
        #    value = float(value_string.replace('V', ''))
        #except ValueError:
        #    value = -999999
        return(value_string)


if __name__ == '__main__':
    ports = {}
    ports[0] = '/dev/serial/by-id/usb-9710_7840-if00-port0'
    ports[1] = '/dev/serial/by-id/usb-9710_7840-if00-port1'
    ports[2] = '/dev/serial/by-id/usb-9710_7840-if00-port2'
    ports[3] = '/dev/serial/by-id/usb-9710_7840-if00-port3'

    dmm = Keithley2700('serial', device=ports[0])
    print(dmm.read_software_version())
    #print(dmm.read_resistance())
