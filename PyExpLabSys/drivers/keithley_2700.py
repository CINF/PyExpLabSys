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

    def fast_voltage(self,):
        command_list = [":SENSE:FUNCTION 'VOLT:DC'", 
                        ":FORMAT:ELEMENT READ", 
                        ":SYSTEM:AZERO:STATE OFF", 
                        ":SENSE:VOLT:DC:AVERAGE:STATE OFF", 
                        ":SENSE:VOLT:DC:NPLC 0.01", 
                        ":SENSE:VOLT:DC:RANGE 10", 
                        ":SENSE:VOLT:DC:DIGITS 4", 
                        ":TRIGGER:COUNT 1", 
                        ":SAMPLE:COUNT 100", 
                        ":TRIGGER:DELAY 0.0", 
                        ":DISPLAY:ENABLE OFF"]
        for command in command_list:
            value_string = self.scpi_comm(command)
            #print(value_string)
        value_string = self.scpi_comm(":READ?")
        try:
            value_split = value_string.split("#")
            print(len(value_split))
            print(value_split[0])
            volts = []
            for v in value_split:
                volts += [float(v.split(",")[0][:-3])]
            value = sum(volts)
        except ValueError:
            value = -999999
        return(value)

    def read_value(self,):
        """Reads the actual output voltage"""
        function_string = ':READ?'
        value_string = self.scpi_comm(function_string)
        data_results = value_string.replace("\r","").split("#")
        values = []
        times = []
        readings = []
        for data_result in data_results[:-1]:
            split = data_result.split(",")
            values += [float(split[0].replace("VDC",""))]
            times += [float(split[1].replace("SECS",""))]
            readings += [int(split[2].replace("RDNG",""))]
        return(values, times, readings)
    
    def setup_voltage(self,):
        self.scpi_comm(":SENSE:FUNC 'VOLT'")
        self.scpi_comm(":FORM:ELEM READ")
        value_string = self.scpi_comm(":READ?")
        return(value_string)

if __name__ == '__main__':
    ports = {}
    ports[0] = '/dev/serial/by-id/usb-9710_7840-if00-port0'
    ports[1] = '/dev/serial/by-id/usb-9710_7840-if00-port1'
    ports[2] = '/dev/serial/by-id/usb-9710_7840-if00-port2'
    ports[3] = '/dev/serial/by-id/usb-9710_7840-if00-port3'

    dmm = Keithley2700('serial', device=ports[0])
    print(dmm.read_software_version())
    #for i in range(10):
    #    print(dmm.read_value())
    #print(dmm.read_resistance())
    print(dmm.read_voltage())
    #print(dmm.fast_voltage())
    print(dmm.setup_voltage)
    print('output')
    for i in range(3):
        print(dmm.read_value())
