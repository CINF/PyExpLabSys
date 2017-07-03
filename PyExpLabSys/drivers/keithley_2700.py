""" Simple driver for Keithley Model 2700 """
from __future__ import print_function
import time
from PyExpLabSys.drivers.scpi import SCPI
from PyExpLabSys.common.supported_versions import python2_and_3
python2_and_3(__file__)

class KeithleySMU(SCPI):
    """ Simple driver for Keithley Model 2700 """

    def __init__(self, interface, device='/dev/ttyUSB0'):
        if interface == 'serial':
            SCPI.__init__(self, interface='serial', device=device, baudrate=9600)
            self.scpi_comm('FORMAT:ELEMENTS READ') # Set short read-format

    def select_measurement_function(self, function):
        """ Select a measurement function.

        Keyword arguments:
        Function -- A string stating the wanted measurement function.

        """

        values = ['CAPACITANCE', 'CONTINUITY', 'CURRENT', 'DIODE', 'FREQUENCY',
                  'RESISTANCE', 'FRESISTANCE', 'TEMPERATURE', 'VOLTAGE']
        return_value = False
        if function in values:
            return_value = True
            function_string = "FUNCTION " + "\"" + function + "\""
            self.scpi_comm(function_string)
        return return_value

    def read(self):
        """ Read a value from the device """
        value = float(self.scpi_comm("READ?"))
        return value
            
if __name__ == '__main__':
    PORT = '/dev/ttyUSB0'

    K2700 = KeithleySMU(interface='serial', device=PORT)
    #K2700.reset_device()
    time.sleep(1)
    print(K2700.read_software_version())
    #print('--')
    #print(K2700.read())
    #print('--')
    #K2700.select_measurement_function('RESISTANCE')
    #print(K2700.read())
    #print('--')
    #K2700.select_measurement_function('TEMPERATURE')
    #print(K2700.read())
    #print('--')
    #print(K2700.scpi_comm('ROUTE:SCAN (@101:108)'))
    #print(K2700.scpi_comm('ROUTE:SCAN?'))
    #print(K2700.scpi_comm('TRIGGER:COUNT 1'))
    #print(K2700.scpi_comm('SAMP:COUNT 8'))
    #print(K2700.scpi_comm('READ?'))
    #print(K2700.scpi_comm('ROUNT:SCAN:NVOL ON'))
    #K2700.scpi_comm('INIT')
    #print(K2700.scpi_comm('READ?'))
    #print(K2700.scpi_comm('ROUTE:SCAN:LSEL NONE'))
    #print(K2700.scpi_comm('CALC1:DATA?'))
    #print(K2700.read())

    K2700.scpi_comm('TRAC:CLE')
    K2700.scpi_comm('INIT:CONT OFF')
    K2700.scpi_comm('TRAC:CLE')
    K2700.scpi_comm('TRIG:SOUR IMM')
    K2700.scpi_comm('TRIG COUN 1')
    K2700.scpi_comm('SAMP:COUNT 1')

    for i in range(1, 11):
        scan_list = '(@1' + str(i).zfill(2) + ')'
        time.sleep(0.25)
        command = "SENS:FUNC 'RESISTANCE', " + scan_list
        print(command)
        K2700.scpi_comm(command)
        time.sleep(0.25)

        K2700.scpi_comm('ROUNT:SCAN ' + scan_list)
        K2700.scpi_comm('ROUT:SCAN:TSO IMM')
        K2700.scpi_comm('ROUT:SCAN:LSEL INT')
        print(K2700.scpi_comm('READ?'))
        K2700.scpi_comm('ROUT:SCAN:LSEL NONE')
